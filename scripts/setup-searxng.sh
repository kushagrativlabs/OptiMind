#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "Docker is required for free local web search. Install it with: brew install colima docker docker-compose"
    exit 1
  fi

  echo "Installing Docker for the local SearXNG search service..."
  sudo apt-get update
  if ! sudo apt-get install -y docker.io docker-compose-v2; then
    sudo apt-get install -y docker.io docker-compose
  fi
  sudo systemctl enable --now docker
fi

docker_command=(docker)
if ! docker info >/dev/null 2>&1; then
  if [[ "$(uname -s)" == "Darwin" ]] && command -v colima >/dev/null 2>&1; then
    echo "Starting the local container runtime..."
    colima start --cpu 2 --memory 4 --disk 20
  elif [[ "$(uname -s)" == "Linux" ]]; then
    docker_command=(sudo docker)
  else
    echo "Docker is installed but is not running."
    exit 1
  fi
fi

if "${docker_command[@]}" compose version >/dev/null 2>&1; then
  compose_command=("${docker_command[@]}" compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose_command=(docker-compose)
else
  echo "Docker Compose is required for SearXNG."
  exit 1
fi

"${compose_command[@]}" -f "${project_root}/infrastructure/compose.yaml" up -d searxng

for _ in {1..30}; do
  if curl -fsS "http://127.0.0.1:8080/" >/dev/null 2>&1; then
    echo "SearXNG is ready at http://127.0.0.1:8080."
    exit 0
  fi
  sleep 1
done

echo "SearXNG did not become ready. Check: docker compose -f infrastructure/compose.yaml logs searxng"
exit 1
