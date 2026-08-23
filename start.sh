#!/usr/bin/env bash
set -e

echo "==> 1. Starting local Redis server..."
redis-server --daemonize yes --protected-mode no

until redis-cli ping > /dev/null 2>&1; do
    echo "Waiting for Redis to start..."
    sleep 1
done
echo "Redis is ready!"

echo "==> 2. Running database migrations & static files..."
python manage.py collectstatic --no-input
python manage.py migrate

echo "==> 3. Starting Celery worker (Optimized for 512MB RAM)..."
celery -A backend worker --loglevel=info --concurrency=1 &

echo "==> 4. Starting Gunicorn web server..."
exec gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 2
