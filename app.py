import psutil
from quart import Quart, request, jsonify, Response
from quart_cors import cors, route_cors
from celery import Celery
import chess
import chess.engine
import chess.pgn
import io
import os
import json
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta
import jwt
import logging
import asyncio

from constants import mongo_uri, JWT_SECRET

app = Quart(__name__)
app = cors(app, allow_origin="*")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MongoDB client
client = MongoClient(mongo_uri, server_api=ServerApi('1'))
try:
    client.admin.command('ping')
    logger.info("MongoDB connection successful!")
except Exception as e:
    logger.error(f"MongoDB connection failed: {e}")

db = client.main
users_collection = db.users


def generate_jwt_token(user: str) -> str:
    expiration_time = datetime.utcnow() + timedelta(minutes=300)
    payload = {'user': user, 'exp': expiration_time}
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

# Celery configuration


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=os.environ.get('CELERY_RESULT_BACKEND',
                               'redis://localhost:6379/0'),
        broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    )
    celery.conf.update(app.config)
    return celery


app.config.update(
    CELERY_BROKER_URL=os.environ.get(
        'CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    CELERY_RESULT_BACKEND=os.environ.get(
        'CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)


celery = make_celery(app)


@app.route("/login", methods=['POST'])
@route_cors(allow_origin="*")
async def login():
    data = await request.json
    user = data.get('user')
    if not user:
        return jsonify({'error': 'User is required'}), 400
    logger.info(f"Logging in user: {user}")
    token = generate_jwt_token(user)
    return jsonify({'token': token})


@app.route("/")
@route_cors(allow_origin="*")
async def index():
    return "home"


@app.route("/deletePuzzle", methods=['DELETE'])
@route_cors(allow_origin="*")
async def deletePuzzle():
    req = await request.get_json()
    user = req.get('user')
    puzzle = req.get('puzzle')

    if not user or not puzzle:
        return jsonify({'error': 'User and puzzle are required'}), 400

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

    result = users_collection.update_one(
        {"user": user},
        {"$pull": {"saved_puzzles": final_puzzle}}
    )

    if result.modified_count > 0:
        return "success, puzzle removed"
    else:
        return "failure, puzzle not found"


@app.route("/savePuzzle", methods=['POST'])
@route_cors(allow_origin="*")
async def savePuzzle():
    req = await request.get_json()
    user = req.get('user')
    puzzle = req.get('puzzle')

    if not user or not puzzle:
        return jsonify({'error': 'User and puzzle are required'}), 400

    logger.info(f"Saving puzzle for user: {user}")

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

    user_doc = users_collection.find_one({"user": user})
    if not user_doc:
        users_collection.insert_one(
            {"user": user, "saved_puzzles": [final_puzzle]})
    else:
        users_collection.update_one(
            {"user": user},
            {"$addToSet": {"saved_puzzles": final_puzzle}}
        )
    return "success"


@app.route("/getPuzzles", methods=['POST'])
@route_cors(allow_origin="*")
async def getPuzzles():
    req = await request.get_json()
    user = req.get('user')

    if not user:
        return jsonify({'error': 'User is required'}), 400

    logger.info(f"Fetching puzzles for user: {user}")

    user_doc = users_collection.find_one({"user": user})
    if not user_doc:
        return jsonify({'puzzles': "no puzzles"})

    return jsonify(user_doc.get("saved_puzzles", []))


def log_resources():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    logger.info(f"Memory Usage: RSS={memory_info.rss}, VMS={memory_info.vms}")
    logger.info(f"CPU Usage: {process.cpu_percent(interval=1.0)}%")


@celery.task
def run_stockfish_analysis(pgn, username):
    log_resources()  # Log resource usage at the start of the task

    game = chess.pgn.read_game(io.StringIO(pgn))
    headers = game.headers

    # stockfish_path = os.path.join(os.getcwd(), 'stockfish')
    stockfish_path = os.path.join(os.getcwd(), 'stockfish-ubuntu')
    logger.info(f"Using Stockfish at: {stockfish_path}")

    try:
        engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        logger.info("Stockfish engine loaded successfully")
    except Exception as e:
        logger.error(f"Could not load Stockfish engine: {e}")
        return {'error': f'Could not load Stockfish engine: {e}'}

    board = game.board()
    user_turn = 'white' if username in headers.get("White") else 'black'
    turn = 'white'
    new_move = 0
    move_number = 1
    potential_tactic = False

    puzzles = []
    prev_potential_tactic = False
    try:
        for move in game.mainline_moves():
            # log_resources()  # Log resource usage periodically
            logger.info(f"Move: {move}, Move Number: {move_number}")

            new_move += 1
            if new_move == 2:
                move_number += 1
                new_move = 0

            before_move_fen = board.fen()
            before_move_info = engine.analyse(
                board, chess.engine.Limit(time=0.05))

            best_move = before_move_info["pv"][0]
            board.push(best_move)
            best_move_fen = board.fen()
            board.pop()

            board.push(move)
            after_move_info = engine.analyse(
                board, chess.engine.Limit(time=0.05))

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

            if potential_tactic and turn == user_turn:
                best_move_diff = abs(best_move_eval - after_move_eval)
                best_move_diff_threshold = 50

                if best_move_diff > best_move_diff_threshold:
                    puzzle = [before_move_fen, best_move_fen, user_turn]
                    puzzles.append(puzzle)

            after_best_diff = abs(after_move_eval - best_move_eval)

            potential_tactic = False
            if not prev_potential_tactic:
                if before_move_eval > 1000 and after_best_diff > 800 and after_move_eval < 200:
                    potential_tactic = True
                elif before_move_eval < -1000 and after_best_diff > 500:
                    potential_tactic = True
                elif before_move_eval > 0 and after_best_diff > 300 and after_move_eval < -250:
                    potential_tactic = True
                elif before_move_eval < 0 and after_best_diff > 300:
                    potential_tactic = True

            prev_potential_tactic = potential_tactic
            turn = 'black' if turn == 'white' else 'white'
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        return {'error': f'Error during analysis: {e}'}
    finally:
        try:
            engine.quit()
        except Exception as e:
            logger.error(f"Error quitting engine: {e}")

    logger.info(f"Puzzles: {puzzles}")
    return {'puzzles': puzzles if puzzles else "no puzzles"}


@app.route("/getTactics", methods=['POST'])
@route_cors(allow_origin="*")
async def getTactics():
    args = await request.get_json()
    pgn = args.get('pgn')
    username = args.get('username')

    if not pgn or not username:
        return jsonify({"error": "User and PGN are required"}), 400

    # Start Celery task
    result = run_stockfish_analysis.delay(pgn, username)

    # Return task ID to the client
    return jsonify({"task_id": result.id})


@app.route("/getTaskResult/<task_id>", methods=['GET'])
@route_cors(allow_origin="*")
async def get_task_result(task_id):
    task = run_stockfish_analysis.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'result': task.result
        }
    else:
        response = {
            'state': task.state,
            'status': str(task.info)
        }
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)
