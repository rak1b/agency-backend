#!/bin/sh

set -e

# Run database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Collect static (in case you want to run it here too)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start gunicorn 
echo "Starting Gunicorn..."
exec gunicorn Config.wsgi:application --bind 0.0.0.0:8000
