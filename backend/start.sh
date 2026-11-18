#!/bin/sh
# Container entrypoint: apply migrations, then start the API.
# `set -e` means a failed migration exits here and uvicorn never starts,
# so the deploy fails loudly instead of serving against a stale schema.
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
