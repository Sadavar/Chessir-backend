import chess
import chess.engine
import chess.pgn
import io
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])


@app.route("/")
def index():
    return "home"

@app.route("/getTactics", methods=['GET'])
def getTactics():
    result = ["tactic1", "tactic2", "tactic3"]
    response = jsonify(result)

    pgn = request.args.get('pgns')
    pgn = io.StringIO(pgn)
    game = chess.pgn.read_game(pgn)
    # engine = chess.engine.SimpleEngine.popen_uci("stockfish")

    return response

# print("python working!")
# quit()
#
# data = open('src/main/python/pgn.txt', 'r').read()
# # data = open('pgn.txt', 'r').read()
# pgn = io.StringIO(data)
# game = chess.pgn.read_game(pgn)
#


# engine = chess.engine.SimpleEngine.popen_uci("src/main/python/stockfish")
# # engine = chess.engine.SimpleEngine.popen_uci("stockfish")
#
# board = game.board()
#
# move_number = 1
# turn_counter = 0
# prev_score = 0
# tactics = []
#
# for move in game.mainline_moves():
#     board.push(move)
#     turn_counter += 1
#
#     info = engine.analyse(board, chess.engine.Limit(time=0.05))
#     curr_score = info["score"].black().score()
#     # print("Move:", move_number, move, "Score:", curr_score)
#     if curr_score is None:
#         continue
#
#     if turn_counter == 1:
#         diff = curr_score - prev_score
#         if diff > 200:
#             # print("Best: ", move)
#             move = info["pv"][0]
#
#             current_fen = board.fen()
#             board.push(move)
#             best_fen = board.fen()
#             board.pop()
#
#             puzzle = [current_fen, best_fen]
#             tactics.append(puzzle)
#
#     if turn_counter == 2:
#         prev_score = info["score"].black().score()
#         move_number += 1
#         turn_counter = 0
#
# for tactic in tactics:
#     print(tactic[0])
#     print(tactic[1])
#
#
# engine.quit()
# quit()
