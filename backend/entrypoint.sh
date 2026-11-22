#!/bin/sh
set -e

echo "==> [AskDesk Backend] Initializing production container runtime..."

# Wait for database availability when DB_HOST is configured
if [ -n "$DB_HOST" ]; then
    echo "==> [AskDesk Backend] Probing database connection at ${DB_HOST}:${DB_PORT:-5432}..."
    RETRY_COUNT=0
    MAX_RETRIES=30
    until python -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.settimeout(2.0)
    s.connect(('${DB_HOST}', int('${DB_PORT:-5432}')))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
            echo "==> [AskDesk Backend] ERROR: Database connection timed out after $MAX_RETRIES attempts."
            exit 1
        fi
        echo "==> [AskDesk Backend] Database not ready yet ($RETRY_COUNT/$MAX_RETRIES)... waiting 1s"
        sleep 1
    done
    echo "==> [AskDesk Backend] Database connection successfully established."
fi

# Run Django database migrations
echo "==> [AskDesk Backend] Applying database migrations..."
python manage.py migrate --no-input

# Collect static assets for production serving
echo "==> [AskDesk Backend] Collecting static files..."
python manage.py collectstatic --no-input --clear || true

echo "==> [AskDesk Backend] Startup checks passed. Executing server process: $@"
exec "$@"
