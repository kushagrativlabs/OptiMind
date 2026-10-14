#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${project_root}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${project_root}/.env"
  set +a
fi

api_host="${API_HOST:-127.0.0.1}"
api_port="${API_PORT:-8000}"
frontend_host="${VITE_HOST:-0.0.0.0}"
frontend_port="${VITE_PORT:-5173}"

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

echo "Starting OptiMind API at http://${api_host}:${api_port}..."
(
  cd "${project_root}/backend"
  .venv/bin/uvicorn app.main:app --reload --host "${api_host}" --port "${api_port}"
) &
api_pid=$!

echo "Starting OptiMind frontend on ${frontend_host}:${frontend_port}..."
npm run dev --prefix "${project_root}/frontend" -- \
  --host "${frontend_host}" \
  --port "${frontend_port}" &
web_pid=$!

while kill -0 "${api_pid}" >/dev/null 2>&1 && kill -0 "${web_pid}" >/dev/null 2>&1; do
  sleep 2
done

echo "An OptiMind service stopped unexpectedly."
exit 1

