#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash "${project_root}/scripts/start-infrastructure.sh"
bash "${project_root}/scripts/create-database.sh"

(
  cd "${project_root}/backend"
  .venv/bin/alembic upgrade head
)

cleanup() {
  kill "${api_pid:-}" "${web_pid:-}" >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

echo "Starting OptiMind API at http://127.0.0.1:8000..."
(
  cd "${project_root}/backend"
  .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) &
api_pid=$!

echo "Starting OptiMind frontend at http://127.0.0.1:5173..."
npm run dev --prefix "${project_root}/frontend" -- --host 127.0.0.1 &
web_pid=$!

while kill -0 "${api_pid}" >/dev/null 2>&1 && kill -0 "${web_pid}" >/dev/null 2>&1; do
  sleep 2
done

echo "An OptiMind service stopped unexpectedly."
exit 1

