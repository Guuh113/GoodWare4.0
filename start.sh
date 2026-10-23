#!/bin/sh
set -eu
python manage.py init-db
exec gunicorn 'app:create_app()' --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --threads 2 --timeout 90 --max-requests 300 --max-requests-jitter 50 --error-logfile -
