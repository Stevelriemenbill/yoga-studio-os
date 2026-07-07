#!/usr/bin/env sh
set -e

echo "Waiting for database..."
until python -c "import asyncio, asyncpg, os; asyncio.run(asyncpg.connect(host=os.environ['POSTGRES_HOST'], port=int(os.environ['POSTGRES_PORT']), user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'], database=os.environ['POSTGRES_DB']))" 2>/dev/null; do
  echo "  db not ready, retrying in 2s..."
  sleep 2
done

echo "Running migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
