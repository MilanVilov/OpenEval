#!/bin/bash
set -e

if [[ "${APP_MYSQL_CLIENT_HOST:-}" =~ ^(localhost|127\.0\.0\.1)$ ]] && [[ -f /.dockerenv ]]; then
    export APP_MYSQL_CLIENT_HOST="host.docker.internal"
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting OpenEval server..."
exec uvicorn src.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}"
