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
  echo "Starting PostgreSQL..."
  case "$(uname -s)" in
    Darwin)
      brew services start postgresql@17
      ;;
    Linux)
      sudo systemctl start postgresql
      ;;
    *)
      echo "PostgreSQL is not running. Start it and run npm start again."
      exit 1
      ;;
  esac

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
  echo "Starting Ollama with ${OLLAMA_NUM_PARALLEL:-2} parallel requests..."
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

image_generation_enabled="${IMAGE_GENERATION_ENABLED:-false}"
if [[ "${image_generation_enabled}" == "true" || "${image_generation_enabled}" == "TRUE" || "${image_generation_enabled}" == "1" ]]; then
  image_generation_url="${IMAGE_GENERATION_BASE_URL:-http://localhost:1234}"
  if ! curl -fsS "${image_generation_url}/v1/models" >/dev/null 2>&1; then
    image_generation_log="${TMPDIR:-/tmp}/optimind-image-generation.log"
    echo "Starting the local image generator..."
    nohup bash "${project_root}/scripts/start-image-generation.sh" >"${image_generation_log}" 2>&1 &
  fi

  for _ in {1..60}; do
    if curl -fsS "${image_generation_url}/v1/models" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  if ! curl -fsS "${image_generation_url}/v1/models" >/dev/null 2>&1; then
    echo "Image generator did not become ready. See ${image_generation_log:-the service log}."
    exit 1
  fi
fi

web_search_enabled="${WEB_SEARCH_ENABLED:-false}"
if [[ "${web_search_enabled}" == "true" || "${web_search_enabled}" == "TRUE" || "${web_search_enabled}" == "1" ]]; then
  searxng_url="${SEARXNG_BASE_URL:-http://localhost:8080}"
  if ! curl -fsS "${searxng_url}/" >/dev/null 2>&1; then
    echo "Starting the free local SearXNG service..."
    bash "${project_root}/scripts/setup-searxng.sh"
  fi
  if ! curl -fsS "${searxng_url}/" >/dev/null 2>&1; then
    echo "SearXNG did not become ready."
    exit 1
  fi
fi

echo "PostgreSQL, Ollama, and configured search/image services are ready."

