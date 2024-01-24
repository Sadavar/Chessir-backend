from os import getcwd
from json import dumps
from io import StringIO
from chess.pgn import read_game, Game
from chess.engine import SimpleEngine, Limit
from chess import WHITE, BLACK


def go_to_move(game: Game, move_number: int, to_move: WHITE | BLACK) -> str:
    """
        This function takes a game and a move number and returns the fen of the board at that move number
        :argument game: chess.pgn.Game
        :argument move_number: int
        :argument to_move: chess.WHITE | chess.BLACK
        :returns: str
    """
    board = game.board()
    mainline_moves = game.mainline_moves()
    for move in mainline_moves:
        if board.fullmove_number == move_number:
            if board.turn == to_move:
                break
        board.push(move)
    return board.fen()


def algo(args):
    puzzles = []
    # read request args
    pgn = args.get('pgn')
    pgn = StringIO(pgn)
    username = args.get('username')
    game = read_game(pgn)
    headers = game.headers

    # configure game and engine
    # engine = chess.engine.SimpleEngine.popen_uci(
    #     os.getcwd() + '/stockfish')
    engine = SimpleEngine.popen_uci(
        getcwd() + '/stockfish-ubuntu')
    board = game.board()

    # configure board settings
    user_turn = 'white' if username in headers.get("White") else 'black'
    turn = 'white'
    new_move = 0
    move_number = 1
    potential_tactic = False

    # simulate moves
    for move in game.mainline_moves():
        # print("\nmove: " + str(move) + ", move number: " + str(move_number))
        # print("turn: " + turn + ", user_turn: " + user_turn)

        # increment move number
        new_move += 1
        if new_move == 2:
            move_number += 1
            new_move = 0

        # get before move info
        before_move_fen = board.fen()
        before_move_info = engine.analyse(
            board, Limit(time=0.05))

        # get best move info
        best_move = before_move_info["pv"][0]
        board.push(best_move)
        best_move_fen = board.fen()
        board.pop()

        # get after move info
        board.push(move)
        after_move_info = engine.analyse(
            board, Limit(time=0.05))

        # set move evals
        if before_move_info["score"].white().score() is None:
            continue
        if after_move_info["score"].white().score() is None:
            continue

        if turn == 'white':
            before_move_eval = before_move_info["score"].white().score()
            best_move_eval = before_move_eval
            after_move_eval = after_move_info["score"].white().score()
        else:
            before_move_eval = before_move_info["score"].black().score()
            best_move_eval = before_move_eval
            after_move_eval = after_move_info["score"].black().score()

        # check if oppenent made a bad move
        if potential_tactic == True and turn == user_turn:
            best_move_diff = abs(best_move_eval - after_move_eval)
            best_move_diff_threshold = 50
            # check if the tactic was missed by threshold, a decent but not best move is allowed
            # print("best_move_diff: " + str(best_move_diff))
            if best_move_diff > best_move_diff_threshold:
                puzzle = [before_move_fen, best_move_fen, user_turn]
                puzzles.append(puzzle)
                print("Found tactic, puzzle:")
                print(puzzle)

        # check blunder
        # calculate score difference between after_move and best_move (+50 -> -70 = |120|)
        after_best_diff = abs(after_move_eval - best_move_eval)
        if turn == user_turn:
            yield dumps({"eval": str(before_move_eval)})

        prev_potential_tactic = potential_tactic
        potential_tactic = False

        if not prev_potential_tactic:
            # if extremely winning -> barely winning
            if before_move_eval > 1000:
                if after_best_diff > 800 and after_move_eval < 200:
                    potential_tactic = True
            # if extremely losing -> super losing
            if before_move_eval < -1000:
                if after_best_diff > 500:
                    potential_tactic = True
            # if barely winning -> losing
            if before_move_eval > 0:
                if after_best_diff > 300 and after_move_eval < -250:
                    potential_tactic = True
            # if barely losing -> extremely losing
            if before_move_eval < 0:
                if after_best_diff > 300:
                    potential_tactic = True

        # change turns
        if turn == 'white':
            turn = 'black'
        else:
            turn = 'white'

    engine.quit()
    print("puzzles:")
    print(puzzles)
    if len(puzzles) == 0:
        yield dumps({"puzzles": "no puzzles"})
    else:
        yield dumps({"puzzles": puzzles})
