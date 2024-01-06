#!/bin/sh

import chess
import chess.engine
import chess.pgn
import io
import os
from flask import Flask, request, jsonify, stream_with_context, Response, redirect, url_for, make_response
from flask_cors import CORS, cross_origin
import json
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

uri = "mongodb+srv://sadavar:99jack@chesstrainer.d0yivsi.mongodb.net/?retryWrites=true&w=majority"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("MongoDB connection successful!")
except Exception as e:
    print(e)

@app.route("/")
@cross_origin()
def index():
    return "home"

@app.route("/savePuzzle", methods=['POST'])
@cross_origin()
def addPuzzle():
    req = request.get_json()
    user = req.get('user')
    puzzle = req.get('puzzle')
    print(user)
    print(puzzle)
    
    db = client.main
    collection = db.users
    
    puzzle_id = collection.create_index("puzzle_id",unique=True)
    
    final_puzzle = {
            "puzzle_id": puzzle_id,
            "start_FEN": puzzle["start_FEN"],
            "end_FEN": puzzle["end_FEN"],
            "turn_color": puzzle["turn_color"]
        }
    
    # check if the user is in the DB
    if(collection.find_one({"user": user}) == None):
        collection.insert_one({"user": user, "puzzles": [final_puzzle]})
    else:
        collection.update_one(
            {"user": user}, 
            {"$addToSet": {"saved_puzzles": final_puzzle}}
        )
    return "success"

@app.route("/getPuzzles", methods=['POST'])
@cross_origin()
def getPuzzles():
    req = request.get_json()
    user = req.get('user')
    print(user)
    
    db = client.main
    collection = db.users
    # check if the user is in the DB
    if(collection.find_one({"user": user}) == None):
        return "no puzzles"
    else:
        puzzles = collection.find_one({"user": user})["saved_puzzles"]
        return json.dumps(puzzles)
       

@app.route("/getTactics", methods=['POST'])
@cross_origin()
def getTactics():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        return response
    args = request.get_json()
    def algo(): 
        puzzles = []
        # read request args
        # args = request.get_json()
        pgn = args.get('pgn')
        # pgn = open("test1-pgn.txt", "r").read()
        pgn = io.StringIO(pgn)
        username = args.get('username')
        game = chess.pgn.read_game(pgn)
        headers = game.headers
        
        # configure game and engine
        engine = chess.engine.SimpleEngine.popen_uci(os.getcwd() + '/stockfish')
        # engine = chess.engine.SimpleEngine.popen_uci(os.getcwd() + '/stockfish-ubuntu')
        board = game.board()
        
        # configure board settings
        user_turn = 'white' if username in headers.get("White") else 'black'
        turn = 'white'
        new_move = 0
        move_number = 1
        potential_tactic = False
        
        # simulate moves
        for move in game.mainline_moves():
            print("\nmove: " + str(move) + ", move number: " + str(move_number))
            print("turn: " + turn + ", user_turn: " + user_turn)
            
            # increment move number
            new_move += 1
            if(new_move == 2): 
                move_number += 1
                new_move = 0
            
            # get before move info
            before_move_fen = board.fen()
            before_move_info = engine.analyse(board, chess.engine.Limit(time=0.05))

            # get best move info
            best_move = before_move_info["pv"][0]
            board.push(best_move)
            best_move_fen = board.fen()
            board.pop()
            
            # get after move info
            board.push(move)
            after_move_info = engine.analyse(board, chess.engine.Limit(time=0.05))
            
            # set move evals
            if before_move_info["score"].white().score() is None:
                continue
            if after_move_info["score"].white().score() is None:
                continue
            
            if(turn == 'white'):
                before_move_eval = before_move_info["score"].white().score()
                best_move_eval = before_move_eval
                after_move_eval = after_move_info["score"].white().score()
            else:
                before_move_eval = before_move_info["score"].black().score()
                best_move_eval = before_move_eval
                after_move_eval = after_move_info["score"].black().score()
                            
            # check if oppenent made a bad move
            if(potential_tactic == True and turn == user_turn):
                best_move_diff = abs(best_move_eval - after_move_eval)
                best_move_diff_threshold = 50
                # check if the tactic was missed by threshold, a decent but not best move is allowed
                print("best_move_diff: " + str(best_move_diff))
                if(best_move_diff > best_move_diff_threshold):
                    puzzle = [before_move_fen, best_move_fen, turn]
                    puzzles.append(puzzle)
            
            # check blunder
            # calculate score difference between after_move and best_move (+50 -> -70 = |120|)
            after_best_diff = abs(after_move_eval - best_move_eval)   
            
            print("checking for blunder")
            print("before_move_eval " + str(before_move_eval) + ", best_move_eval: " + str(best_move_eval) + ", after_move_eval: " + str(after_move_eval))
            print("after_best_diff: " + str(after_best_diff))
            print("after_move_eval: " + str(after_move_eval))
            
            # yield str(after_best_diff) + "\n"
            if(turn == user_turn):
                yield str(before_move_eval) + "\n"
            
            prev_potential_tactic = potential_tactic
            potential_tactic = False
            
            if(prev_potential_tactic == False):
                # if extremely winning -> barely winning
                if(before_move_eval > 1000): 
                    if(after_best_diff > 800 and after_move_eval < 200):
                        print("Blunder!------------------------------------------------!")
                        potential_tactic = True
                # if extremely losing -> super losing
                if(before_move_eval < -1000):
                    if(after_best_diff > 500):
                        print("Blunder!------------------------------------------------!")
                        potential_tactic = True
                # if barely winning -> losing
                if(before_move_eval > 0):
                    if(after_best_diff > 300 and after_move_eval < -250):
                        print("Blunder!------------------------------------------------!")
                        potential_tactic = True
                # if barely losing -> extremely losing
                if(before_move_eval < 0):
                    if(after_best_diff > 300):
                        print("Blunder!------------------------------------------------!")
                        potential_tactic = True

            # change turns
            if(turn == 'white'):
                turn == 'black'
            else:
                turn == 'white'

        engine.quit()

        response = json.dumps(puzzles)
        print(response)
        yield response
    
    return Response(algo(), content_type='text/event-stream')

if __name__ == "__main__":
    app.run(debug="true")
    