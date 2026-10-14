#!/usr/bin/env bash

set -euo pipefail

model_name="${OLLAMA_MODEL:-qwen2.5:3b}"
ollama_log="${TMPDIR:-/tmp}/optimind-ollama.log"

if ! command -v ollama >/dev/null 2>&1; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is required to install Ollama on macOS."
    echo "Install Homebrew from https://brew.sh and run npm run ollama:setup again."
    exit 1
  fi

  echo "Installing Ollama with Homebrew..."
  brew install ollama
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
echo "Ollama and ${model_name} are ready."

