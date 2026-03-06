#!/bin/bash
set -e

echo "⏳ Waiting for database..."
while ! python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.production')
django.setup()
from django.db import connections
connections['default'].ensure_connection()
" 2>/dev/null; do
    echo "  Database unavailable, retrying in 2s..."
    sleep 2
done
echo "✅ Database is ready!"

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "🚀 Starting Gunicorn..."
exec gunicorn core.wsgi:application -c gunicorn.conf.py
