#!/bin/sh
# Entrypoint script that runs migrations before starting the application.
set -e

echo "Running database migrations..."
poetry run alembic upgrade head
echo "Migrations complete."

exec "$@"
