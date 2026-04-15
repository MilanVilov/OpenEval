#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting OpenEval server..."
exec uvicorn src.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}"
