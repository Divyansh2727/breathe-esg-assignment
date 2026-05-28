#!/bin/sh
set -e
cd /app/backend

echo "Waiting for PostgreSQL..."
python << 'PY'
import os
import sys
import time

import psycopg2

url = os.environ.get("DATABASE_URL", "")
for attempt in range(1, 31):
    try:
        psycopg2.connect(url)
        print("Database is ready.")
        sys.exit(0)
    except psycopg2.OperationalError:
        print(f"  attempt {attempt}/30 — not ready yet")
        time.sleep(2)
print("Database did not become ready in time.", file=sys.stderr)
sys.exit(1)
PY

python manage.py migrate --noinput
python manage.py seed_demo 2>/dev/null || true
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2
