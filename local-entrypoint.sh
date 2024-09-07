#!/bin/sh

# Start Redis server with configuration file
redis-server redis.conf &

# Start Celery worker
celery -A celery_worker worker --loglevel=info &

# Start Gunicorn with Uvicorn workers for Quart app
gunicorn -c gunicorn_config.py --worker-class uvicorn.workers.UvicornWorker app:app

# Keep the script running
wait -n