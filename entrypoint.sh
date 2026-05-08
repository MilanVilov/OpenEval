#!/bin/bash
set -e

if [[ -f /.dockerenv ]]; then
    if [[ "${APP_MYSQL_CLIENT_HOST:-}" =~ ^(localhost|127\.0\.0\.1)$ ]]; then
        export APP_MYSQL_CLIENT_HOST="host.docker.internal"
    fi
    if [[ "${DATABASE_URL:-}" == mysql+*://*@localhost:* ]]; then
        export DATABASE_URL="${DATABASE_URL/@localhost:/@host.docker.internal:}"
    fi
    if [[ "${DATABASE_URL:-}" == mysql+*://*@127.0.0.1:* ]]; then
        export DATABASE_URL="${DATABASE_URL/@127.0.0.1:/@host.docker.internal:}"
    fi
fi

should_create_mysql_db=false
if [[ -n "${APP_MYSQL_CLIENT_DB:-}" ]]; then
    if [[ -z "${DATABASE_URL:-}" || "${DATABASE_URL:-}" == mysql+* ]]; then
        should_create_mysql_db=true
    fi
fi

if [[ "$should_create_mysql_db" == "true" ]]; then
    echo "Creating database if needed..."
    openeval-db-create
else
    echo "Skipping database creation."
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting OpenEval server..."
exec uvicorn src.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}"
