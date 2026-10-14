#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${project_root}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${project_root}/.env"
  set +a
fi

db_host="${POSTGRES_HOST:-localhost}"
db_port="${POSTGRES_PORT:-5432}"
pg_isready_bin="$(command -v pg_isready || true)"

if [[ -z "${pg_isready_bin}" && -x /opt/homebrew/opt/postgresql@17/bin/pg_isready ]]; then
  pg_isready_bin="/opt/homebrew/opt/postgresql@17/bin/pg_isready"
fi

if [[ -z "${pg_isready_bin}" ]]; then
  echo "PostgreSQL readiness tool not found. Install PostgreSQL first."
  exit 1
fi

if ! "${pg_isready_bin}" --host "${db_host}" --port "${db_port}" >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1 && brew list postgresql@17 >/dev/null 2>&1; then
    echo "Starting PostgreSQL..."
    brew services start postgresql@17
  else
    echo "PostgreSQL is not running. Start it and run npm start again."
    exit 1
  fi

  for _ in {1..20}; do
    if "${pg_isready_bin}" --host "${db_host}" --port "${db_port}" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

if ! "${pg_isready_bin}" --host "${db_host}" --port "${db_port}" >/dev/null 2>&1; then
  echo "PostgreSQL did not become ready."
  exit 1
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed. Run npm run ollama:setup first."
  exit 1
fi

if ! ollama list >/dev/null 2>&1; then
  ollama_log="${TMPDIR:-/tmp}/optimind-ollama.log"
  echo "Starting Ollama..."
  nohup ollama serve >"${ollama_log}" 2>&1 &

  for _ in {1..20}; do
    if ollama list >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

if ! ollama list >/dev/null 2>&1; then
  echo "Ollama did not become ready."
  exit 1
fi

echo "PostgreSQL and Ollama are ready."

