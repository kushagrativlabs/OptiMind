#!/usr/bin/env bash

set -euo pipefail

model_name="${OLLAMA_MODEL:-qwen2.5:3b}"
vision_model_name="${OLLAMA_VISION_MODEL:-qwen3.5:0.8b}"
ollama_log="${TMPDIR:-/tmp}/optimind-ollama.log"

if ! command -v ollama >/dev/null 2>&1; then
  case "$(uname -s)" in
    Darwin)
      if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew is required to install Ollama on macOS."
        exit 1
      fi
      echo "Installing Ollama with Homebrew..."
      brew install ollama
      ;;
    Linux)
      if ! command -v curl >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y curl
      fi
      echo "Installing Ollama using the official Linux installer..."
      curl -fsSL https://ollama.com/install.sh | sh
      ;;
    *)
      echo "Automatic Ollama setup is supported on macOS and Linux."
      exit 1
      ;;
  esac
fi

if ! ollama list >/dev/null 2>&1; then
  echo "Starting the Ollama service..."
  nohup ollama serve >"${ollama_log}" 2>&1 &

  for _ in {1..20}; do
    if ollama list >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

if ! ollama list >/dev/null 2>&1; then
  echo "Ollama did not start. See ${ollama_log} for details."
  exit 1
fi

echo "Installing model ${model_name}..."
ollama pull "${model_name}"
if [[ "${vision_model_name}" != "${model_name}" ]]; then
  echo "Installing lightweight vision model ${vision_model_name}..."
  ollama pull "${vision_model_name}"
fi
echo "Ollama, ${model_name}, and image processing are ready."

