#!/bin/sh
# `npm run backend`: Postgres + Redis (backend/docker-compose.yml), migrations, the admin login from backend/.env,
# then the Celery worker with beat (periodic syncs) and Django on 127.0.0.1:8000. Ctrl+C stops all of it.
# Anything already listening on port 8000 is stopped first.
set -eu

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/backend"

if [ ! -f .env ]; then
    echo "backend/.env is missing: copy backend/.env.example to backend/.env" >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "Docker isn't running: start Docker Desktop and try again" >&2
    exit 1
fi

# Free 127.0.0.1:8000 if one of *your* processes holds it (an old runserver). Listeners bound to another address,
# like vLLM on hacknation-dev's tailnet IP (100.78.88.117:8000), don't block 127.0.0.1 and are left alone.
port_pids() {
    if command -v ss >/dev/null 2>&1; then
        ss -ltnpH 2>/dev/null | awk '$4 ~ /^(127\.0\.0\.1|0\.0\.0\.0|\*|\[::\]|\[::1\]):8000$/' |
            grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u
    elif command -v lsof >/dev/null 2>&1; then
        lsof -t -a -u "$(id -u)" -iTCP@127.0.0.1:8000 -sTCP:LISTEN 2>/dev/null || true
    fi
}
pids="$(port_pids | tr '\n' ' ')"
if [ -n "${pids% }" ]; then
    echo "Stopping what was listening on 127.0.0.1:8000 (pid $pids)"
    kill $pids 2>/dev/null || true
    sleep 1
fi

uv sync -q
docker compose --env-file .env up -d --wait postgres redis
uv run python manage.py migrate --noinput
uv run python manage.py seed_integrations
uv run python manage.py ensure_admin
# Municipality boundaries for teryt/city from coordinates: a ~70 MB download the first time, then a no-op
uv run python manage.py load_boundaries --if-missing || echo "Boundaries not loaded (offline?): teryt/city stay empty" >&2

uv run celery -A config worker --beat --loglevel=INFO --concurrency=2 \
    --schedule="$root/backend/var/celerybeat-schedule" &
worker=$!
uv run python manage.py runserver 127.0.0.1:8000 &
server=$!
trap 'kill "$server" "$worker" 2>/dev/null; wait 2>/dev/null' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
wait "$server"
