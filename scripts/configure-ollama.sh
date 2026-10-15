#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${project_root}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${project_root}/.env"
  set +a
fi

parallel_requests="${OLLAMA_NUM_PARALLEL:-2}"
max_loaded_models="${OLLAMA_MAX_LOADED_MODELS:-1}"

case "$(uname -s)" in
  Darwin)
    launchctl setenv OLLAMA_NUM_PARALLEL "${parallel_requests}"
    launchctl setenv OLLAMA_MAX_LOADED_MODELS "${max_loaded_models}"
    echo "Ollama is configured for ${parallel_requests} parallel requests."
    echo "Restart the Ollama app once for this setting to take effect."
    ;;
  Linux)
    echo "Add these values to the environment of your Ollama systemd service:"
    echo "  OLLAMA_NUM_PARALLEL=${parallel_requests}"
    echo "  OLLAMA_MAX_LOADED_MODELS=${max_loaded_models}"
    echo "Then restart Ollama with: sudo systemctl restart ollama"
    ;;
  *)
    echo "Start Ollama with these environment values:"
    echo "  OLLAMA_NUM_PARALLEL=${parallel_requests}"
    echo "  OLLAMA_MAX_LOADED_MODELS=${max_loaded_models}"
    ;;
esac
