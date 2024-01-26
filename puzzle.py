from os import getcwd
from json import dumps
from io import StringIO
from chess.pgn import read_game, Game
from chess import Board, Move
from chess.engine import SimpleEngine, Limit
from chess import WHITE, BLACK
from typing import List, Callable


def go_to_move(game: Game, move_number: int, to_move: WHITE | BLACK,
               callback: Callable[[Game, Board, Move], any]) -> Board:
    """
        This function takes a game and a move number and returns the board at that move number
        :argument game: chess.pgn.Game
        :argument move_number: int
        :argument to_move: chess.WHITE | chess.BLACK
        :argument callback: Callable[[Move], any] - function to call once the move is found
        :returns: str
    """
    board = game.board()
    mainline_moves = game.mainline_moves()
    for move in mainline_moves:
        if board.fullmove_number == move_number:
            if board.turn == to_move:
                callback(game, board, move)
        board.push(move)
    return board


def analyze_move(board: Board, before_move: dict, played_move: dict, user_turn: WHITE | BLACK,
                 potential_tactic: bool) -> str | None:
    turn = 'white' if board.turn == WHITE else 'black'

    before_move_fen = board.fen()

    best_move = before_move["pv"][0]
    board.push(best_move)
    best_move_fen = board.fen()
    board.pop()

    # set move evals
    if before_move["score"].white().score() is None or played_move["score"].white().score() is None:
        return None

    before_move_eval = before_move["score"].white().score() if board.turn == WHITE \
        else before_move["score"].black().score()
    played_move_eval = played_move["score"].white().score() if board.turn == WHITE \
        else played_move["score"].black().score()

    # check if opponent made a bad move
    if potential_tactic and board.turn == user_turn:
        best_move_diff = abs(before_move_eval - played_move_eval)
        threshold = 50
        # check if the tactic was missed by threshold, a decent but not best move is allowed
        if best_move_diff > threshold:
            puzzle = [before_move_fen, best_move_fen, turn]
            print("Found tactic, puzzle:")
            print(puzzle)
            return puzzle

    # check blunder
    # calculate score difference between after_move and best_move (+50 -> -70 = |120|)
    if board.turn == user_turn:
        return [None, None, turn, played_move_eval]

    return None


def calculate_potential(potential_tactic: bool, before_move: int, eval_delta: int, played_move: int) -> bool:
    if not potential_tactic:
        # if extremely winning -> barely winning
        if before_move > 1000:
            if eval_delta > 800 and played_move < 200:
                return True
        # if extremely losing -> super losing
        if before_move < -1000:
            # TODO: Why do we not have to check if played_move_eval is less than -1000?
            if eval_delta > 500:
                return True
        # if barely winning -> losing
        if before_move > 0:
            if eval_delta > 300 and played_move < -250:
                return True
        # if barely losing -> extremely losing
        if before_move < 0:
            # TODO: Why do we not have to check if played_move_eval is less than -250?
            if eval_delta > 300:
                return True
    return False


def find_tactics(game: Game, engine: SimpleEngine, user_turn: WHITE | BLACK) -> List:
    out = []
    board = game.board()
    potential_tactic = False
    for move in game.mainline_moves():
        before_move = engine.analyse(board, Limit(time=0.05))
        board.push(move)
        played_move = engine.analyse(board, Limit(time=0.05))
        board.pop()

        before_move_eval = before_move["score"].white().score() if board.turn == WHITE \
            else before_move["score"].black().score()
        played_move_eval = played_move["score"].white().score() if board.turn == WHITE \
            else played_move["score"].black().score()

        # Analyze current move
        if tactic_found := analyze_move(board, before_move, played_move, user_turn, potential_tactic):
            out.append(tactic_found)

        potential_tactic = calculate_potential(potential_tactic,
                                               before_move_eval,
                                               abs(before_move_eval - played_move_eval),
                                               played_move_eval)

        # push move to board
        board.push(move)

    return out


def analyze_pgn(pgn, username):
    # read request args
    pgn = StringIO(pgn)
    game = read_game(pgn)
    headers = game.headers

    # https://stackoverflow.com/questions/32815451/are-global-variables-thread-safe-in-flask-how-do-i-share-data-between-requests
    # DO NOT CHANGE, SERVER WILL CRASH TODO: fix
    engine = SimpleEngine.popen_uci(getcwd() + '/stockfish-ubuntu')

    user_turn = WHITE if headers['White'] == username else BLACK

    puzzles = find_tactics(game, engine, user_turn)

    engine.quit()
    print("puzzles:")
    print(puzzles)
    # TODO: Return puzzles
    if len(puzzles) == 0:
        yield dumps({"puzzles": "no puzzles"})
    else:
        yield dumps({"puzzles": puzzles})
