#!/bin/sh

import chess
import chess.engine
import chess.pgn
import io
import os
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import json

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return "home"

@app.route("/getTactics", methods=['POST'])
def getTactics():
    puzzles = []
    # read request args
    args = request.get_json()
    pgn = args.get('pgn')
    username = args.get('username')

    pgn = io.StringIO(pgn)
    game = chess.pgn.read_game(pgn)
    headers = game.headers

    # configure game and engine
    engine = chess.engine.SimpleEngine.popen_uci(os.getcwd() + '/stockfish')
    board = game.board()

    user_turn = 'white' if username in headers.get("White") else 'black'

    prev_turn_score = 0
    turn = 'white'
    move_number = 0
    # simulate moves
    for move in game.mainline_moves():
        move_number += 1
        print("move: " + str(move) + ", move number: " + str(move_number))
        # get eval of position 
        start_fen = board.fen()
        info = engine.analyse(board, chess.engine.Limit(time=0.05))
        if info["score"].white().score() is None:
            continue

        before_score_white = info["score"].white().score()
        before_score_black = before_score_white * -1

        # get best move
        best_move = info["pv"][0]
        # play move in game
        board.push(move)
        # get eval after move
        info = engine.analyse(board, chess.engine.Limit(time=0.05))
        if info["score"].white().score() is None:
            continue
    
        after_score_white = info["score"].white().score()
        after_score_black = after_score_white * -1

        tactic_threshold = 300
        print("prev_turn_score: " + str(prev_turn_score) + ", turn: " + turn + ", user_turn: " + user_turn)
        # check if oppenent made a bad move
        if(prev_turn_score > tactic_threshold and turn == user_turn):
            # check if the tactic was missed
            board.pop()
            board.push(best_move)
            info = engine.analyse(board, chess.engine.Limit(time=0.05))
            board.pop()
            # check if score is None
            if info["score"].white().score() is None:
                board.push(move)
                continue
            
            # calculate the difference in score between the best move and the move played
            if(turn == 'white'):
                best_score = info["score"].white().score()
                best_move_diff = abs(best_score - after_score_white)
            else:
                best_score = info["score"].black().score()
                best_move_diff = abs(best_score - after_score_black)
                
            best_move_diff_threshold = 50
            # check if the tactic was missed by threshold, a decent but not best move is allowed
            print("best_move_diff: " + str(best_move_diff))
            if(best_move_diff > best_move_diff_threshold):
                board.push(best_move)
                best_fen = board.fen()
                board.pop()
                puzzle = [start_fen, best_fen, turn]
                puzzles.append(puzzle)
            
            board.push(move)
        
        match turn:
            case 'white':
                prev_turn_score = abs(after_score_white - before_score_white)
                turn = 'black'
            case 'black':
                prev_turn_score = abs(after_score_black - before_score_black)
                turn = 'white'

    engine.quit()

    response = json.dumps(puzzles)
    print(response)
    return response