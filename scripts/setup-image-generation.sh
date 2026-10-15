#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_dir="${IMAGE_GENERATION_RUNTIME_DIR:-${project_root}/.local/stable-diffusion.cpp}"
models_dir="${IMAGE_GENERATION_MODELS_DIR:-${project_root}/.local/image-models}"
model_path="${models_dir}/stable-diffusion-v1-5-pruned-emaonly-Q4_0.gguf"
model_url="https://huggingface.co/second-state/stable-diffusion-v1-5-GGUF/resolve/main/stable-diffusion-v1-5-pruned-emaonly-Q4_0.gguf?download=true"

if ! command -v cmake >/dev/null 2>&1; then
  echo "Installing the image generator build tools..."
  case "$(uname -s)" in
    Darwin)
      command -v brew >/dev/null 2>&1 || {
        echo "Homebrew is required to install CMake on macOS."
        exit 1
      }
      brew install cmake
      ;;
    Linux)
      sudo apt-get update
      sudo apt-get install -y build-essential cmake
      ;;
    *)
      echo "Install CMake and a C++ compiler, then run this command again."
      exit 1
      ;;
  esac
fi

mkdir -p "$(dirname "${runtime_dir}")" "${models_dir}"

if [[ ! -d "${runtime_dir}/.git" ]]; then
  echo "Downloading stable-diffusion.cpp..."
  git clone --recursive https://github.com/leejet/stable-diffusion.cpp "${runtime_dir}"
else
  echo "Updating stable-diffusion.cpp..."
  git -C "${runtime_dir}" pull --ff-only
  git -C "${runtime_dir}" submodule update --init --recursive
fi

cmake_args=(
  -S "${runtime_dir}"
  -B "${runtime_dir}/build"
  -DSD_WEBM=OFF
  -DSD_SERVER_BUILD_FRONTEND=OFF
)
if [[ "$(uname -s)" == "Darwin" ]]; then
  cmake_args+=(-DSD_METAL=ON)
fi

echo "Building the local image generator..."
cmake "${cmake_args[@]}"
cmake --build "${runtime_dir}/build" --config Release -j 2

if [[ ! -f "${model_path}" ]]; then
  echo "Downloading the 1.57 GB quantized Stable Diffusion model..."
  curl --fail --location --retry 3 --continue-at - --output "${model_path}" "${model_url}"
fi

echo "Image generation setup is ready. Run: npm run image:start"
