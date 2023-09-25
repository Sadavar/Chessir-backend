#!/bin/sh
import chess
import chess.engine
import chess.pgn
import io
import os
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import json

__name__ = "__analyze__"

def getTactics2():
    puzzles = []
    # read pgn 
    pgn = open("pgn.txt", "r").read()
    pgn = io.StringIO(pgn)
    
    # configure game and engine
    game = chess.pgn.read_game(pgn)
    engine = chess.engine.SimpleEngine.popen_uci(os.getcwd() + '/stockfish')
    board = game.board()

    move_counter = 1
    prev_turn_score = 0
    turn = 'white'
    # simulate moves
    for move in game.mainline_moves():
        # get eval of position 
        start_fen = board.fen()
        info = engine.analyse(board, chess.engine.Limit(time=0.05))
        before_score_white = info["score"].white().score()
        before_score_black = before_score_white * -1

        if before_score_white is None or before_score_black is None:
            continue

        # get best move
        best_move = info["pv"][0]
        # play move in game
        board.push(move)
        # get eval after move
        info = engine.analyse(board, chess.engine.Limit(time=0.05))
        after_score_white = info["score"].white().score()
        after_score_black = after_score_white * -1

        print("Move:", move_counter, ",", move, "Turn:", turn)
        print("Before White Score: ", before_score_white, "Before Black Score:", before_score_black)
        print("After White Score: ", after_score_white, "After Black Score:", after_score_black)

        tactic_threshold = 300
        # check if oppenent made a bad move
        if(prev_turn_score > tactic_threshold):
            # check if the tactic was missed
            print("move: ", move, "best_move: ", best_move)
            board.pop()
            board.push(best_move)
            info = engine.analyse(board, chess.engine.Limit(time=0.05))
            board.pop()
            
            # calculate the difference in score between the best move and the move played
            if(turn == 'white'):
                best_score = info["score"].white().score()
                best_move_diff = abs(best_score - after_score_white)
            if(turn == 'black'):
                best_score = info["score"].black().score()
                best_move_diff = abs(best_score - after_score_black)
                
            print("Best Score: ", best_score)

            best_move_diff_threshold = 50
            # check if the tactic was missed by threshold, a decent but not best move is allowed
            if(best_move_diff > best_move_diff_threshold):
                print("Tactic Missed----------------------------------------------------")
                print("Best Move: ", best_move, "Best Score: ", best_score)

                board.push(best_move)
                best_fen = board.fen()
                puzzle = [start_fen, best_fen]
                puzzles.append(puzzle)
                board.pop()
            
            board.push(move)
            

        if(turn == 'white'): turn = 'black'
        else: turn = 'white'
            
        if(turn == 'white'): 
            prev_turn_score = abs(after_score_white - before_score_white)
        if(turn == 'black'): 
            prev_turn_score = abs(after_score_black - before_score_black)

        move_counter += 1
    
    engine.quit()

    # print out puzzles 
    for puzzle in puzzles:
        print(puzzle[0])
        print(puzzle[1])

    response = json.dumps(puzzles)
    print(response)
    return response


def getTactics():
    # result = ["tactic1", "tactic2", "tactic3"]
    result = []
    result.append(os.getcwd())
    result.append(os.listdir())

    # read pgn from pgn.txt
    pgn = open("pgn.txt", "r").read()    
    # pgn = request.get_json()
    
    # response = jsonify(result)


    # pgn = request.args.get('pgns')
    print("pgn: " + pgn)
    pgn = io.StringIO(pgn)
    game = chess.pgn.read_game(pgn)
    # engine = chess.engine.SimpleEngine.popen_uci(os.getcwd() + "/stockfish-ubuntu")
    engine = chess.engine.SimpleEngine.popen_uci(os.getcwd() + '/stockfish')

    board = game.board()

    move_number = 1
    turn_counter = 0
    prev_score = 0
    tactics = []
    output = []

    for move in game.mainline_moves():
        board.push(move)
        turn_counter += 1

        info = engine.analyse(board, chess.engine.Limit(time=0.05))
        curr_score = info["score"].black().score()
        # print("Move:", move_number, move, "Score:", curr_score)



        if curr_score is None:
            continue

        if turn_counter == 1:
            diff = curr_score - prev_score
            if diff > 200:
                # print("Best: ", move)
                move = info["pv"][0]

                current_fen = board.fen()
                board.push(move)
                best_fen = board.fen()
                board.pop()

                puzzle = [current_fen, best_fen]
                tactics.append(puzzle)

        if turn_counter == 2:
            prev_score = info["score"].black().score()
            move_number += 1
            turn_counter = 0

    for tactic in tactics:
        output.append(tactic[0])
        output.append(tactic[1])

    engine.quit()

    # response = jsonify(output)
    response = json.dumps(output)
    print(response)

    return response

def main():

    getTactics2()

if __name__ == "__analyze__":
    main()