#!/bin/sh
set -e

host="${DB_HOST:-postgres}"
port="${DB_PORT:-5432}"

# wait for postgres to be ready
max_wait=60
i=0
while ! pg_isready -h "$host" -p "$port" >/dev/null 2>&1; do
  i=$((i+1))
  if [ "$i" -ge "$max_wait" ]; then
    echo "Postgres did not become ready in time"
    exit 1
  fi
  echo "Waiting for Postgres... ($i)"
  sleep 1
done

# if no args provided, just exit
if [ "$#" -eq 0 ]; then
  exit 0
fi

exec "$@"
