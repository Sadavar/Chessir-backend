#!/bin/sh

from puzzle import analyze_pgn
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import json
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta
import jwt
from constants import mongo_uri

app = Flask(__name__)
# cors = CORS(app)
# set CORS only for localhost:3000
# cors = CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})
# app.config['CORS_HEADERS'] = 'Content-Type'

# app.config['CORS_HEADERS'] = 'Content-Type'
# CORS(app, resources={r"/*": {"origins": "*"}})

CORS(app)

# Create a new client and connect to the server
client = MongoClient(mongo_uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("MongoDB connection successful!")
except Exception as e:
    print(e)


@app.route("/login", methods=['POST'])
def login():
    user = request.get_json().get('user')
    print("logging in user: " + user)
    # Token expiration time (e.g., 30 minutes)
    expiration_time = datetime.utcnow() + timedelta(minutes=300)
    payload = {
        'user': user,
        'exp': expiration_time,
    }
    token = jwt.encode(
        payload, "examplekey", algorithm='HS256')

    return jsonify({'token': token})


@app.route("/")
def index():
    return "home"


@app.route("/deletePuzzle", methods=['DELETE'])
def deletePuzzle():
    req = request.get_json()
    user = req.get('user')
    puzzle = req.get('puzzle')
    print(user)
    print(puzzle)

    db = client.main
    collection = db.users

    game_info = puzzle["game_info"]

    final_puzzle = {
        "start_FEN": puzzle["start_FEN"],
        "end_FEN": puzzle["end_FEN"],
        "turn_color": puzzle["turn_color"],
        "name": puzzle["name"],
        "game_info": {
            "black": game_info["black"],
            "black_elo": game_info["black_elo"],
            "date": game_info["date"],
            "link": game_info["link"],
            "result": game_info["result"],
            "time_control": game_info["time_control"],
            "white": game_info["white"],
            "white_elo": game_info["white_elo"]
        },
        "date_info": {
            "date": puzzle["date_info"]["date"],
            "timestamp": puzzle["date_info"]["timestamp"]
        }
    }

    collection.update_one(
        {"user": user},
        {"$pull": {"saved_puzzles": final_puzzle}}
    )
    # check if that puzzle is still in saved_puzzles
    if collection.find_one({"user": user, "saved_puzzles": final_puzzle}) is None:
        return "success, puzzle removed"
    else:
        return "failure, puzzle is still in saved puzzles"


@app.route("/savePuzzle", methods=['POST'])
def savePuzzle():
    req = request.get_json()
    user = req.get('user')
    puzzle = req.get('puzzle')
    print(user)
    print(puzzle)

    db = client.main
    collection = db.users

    game_info = puzzle["game_info"]

    final_puzzle = {
        "start_FEN": puzzle["start_FEN"],
        "end_FEN": puzzle["end_FEN"],
        "turn_color": puzzle["turn_color"],
        "name": puzzle["name"],
        "game_info": {
            "black": game_info["black"],
            "black_elo": game_info["black_elo"],
            "date": game_info["date"],
            "link": game_info["link"],
            "result": game_info["result"],
            "time_control": game_info["time_control"],
            "white": game_info["white"],
            "white_elo": game_info["white_elo"]
        },
        "date_info": {
            "date": puzzle["date_info"]["date"],
            "timestamp": puzzle["date_info"]["timestamp"]
        }
    }

    # check if the user is in the DB
    if collection.find_one({"user": user}) is None:
        collection.insert_one({"user": user, "saved_puzzles": [final_puzzle]})
    else:
        collection.update_one(
            {"user": user},
            {"$addToSet": {"saved_puzzles": final_puzzle}}
        )
    return "success"


@app.route("/getPuzzles", methods=['POST'])
def getPuzzles():
    req = request.get_json()
    user = req.get('user')
    print(user)

    db = client.main
    collection = db.users
    # check if the user is in the DB
    if collection.find_one({"user": user}) is None:
        return "no puzzles"
    else:
        puzzles = collection.find_one({"user": user})["saved_puzzles"]
        return json.dumps(puzzles)


@app.route("/getTactics", methods=['POST'])
def getTactics():
    args = request.get_json()
    return Response(analyze_pgn(args.get("pgn"), args.get("username")), content_type='text/event-stream')


if __name__ == "__main__":
    app.run(debug=True)
