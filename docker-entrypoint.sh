#!/bin/sh

# Set kernel parameters for Redis directly within the container
echo "Setting vm.overcommit_memory to 1"
sudo sysctl -w vm.overcommit_memory=1

# Check if Stockfish binary runs
# ./stockfish-ubuntu --help || (echo "Stockfish-ubuntu binary failed to run."; exit 1)

# Start Redis server with configuration file
redis-server /app/redis.conf &

# Start Celery worker
celery -A celery_worker worker --loglevel=info &

# Start Gunicorn with Uvicorn workers for Quart app
gunicorn -c gunicorn_config.py --worker-class uvicorn.workers.UvicornWorker app:app

# Keep the script running
wait -n