#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting ai-eval server..."
exec uvicorn ai_eval.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}"
