#!/usr/bin/env bash
set -e

echo "==> 1. Starting local Redis server..."
redis-server --daemonize yes --protected-mode no

# Wait a brief moment for Redis socket to initialize
until redis-cli ping > /dev/null 2>&1; do
    echo "Waiting for Redis to start..."
    sleep 1
done
echo "Redis is ready!"

echo "==> 2. Running database migrations on Aiven..."
python manage.py collectstatic --no-input
python manage.py migrate

echo "==> 3. Starting Celery worker in the background..."
celery -A backend worker --loglevel=info --concurrency=2 &

echo "==> 4. Starting Gunicorn web server on port $PORT..."
exec gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 3