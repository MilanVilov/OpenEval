#!/bin/bash
set -e

if [[ "${DATABASE_URL:-}" == mysql+*://*@localhost:* ]] && [[ -f /.dockerenv ]]; then
    export DATABASE_URL="${DATABASE_URL/@localhost:/@host.docker.internal:}"
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting OpenEval server..."
exec uvicorn src.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}"
