#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${project_root}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${project_root}/.env"
  set +a
fi

runtime_dir="${IMAGE_GENERATION_RUNTIME_DIR:-${project_root}/.local/stable-diffusion.cpp}"
models_dir="${IMAGE_GENERATION_MODELS_DIR:-${project_root}/.local/image-models}"
server_bin="${runtime_dir}/build/bin/sd-server"
model_path="${models_dir}/lcm-ssd-1b.q4_k.gguf"
vae_path="${models_dir}/sdxl_vae.safetensors"
listen_port="${IMAGE_GENERATION_PORT:-1234}"
generation_backend="${IMAGE_GENERATION_BACKEND:-cpu}"

if [[ ! -x "${server_bin}" || ! -f "${model_path}" || ! -f "${vae_path}" ]]; then
  echo "Image generator is not installed. Run npm run image:setup first."
  exit 1
fi

exec "${server_bin}" \
  --model "${model_path}" \
  --vae "${vae_path}" \
  --backend "${generation_backend}" \
  --listen-ip 127.0.0.1 \
  --listen-port "${listen_port}" \
  --steps "${IMAGE_GENERATION_STEPS:-4}" \
  --cfg-scale "${IMAGE_GENERATION_CFG_SCALE:-1.0}" \
  --sampling-method "${IMAGE_GENERATION_SAMPLER:-lcm}" \
  --linear-scale 0.00390625 \
  --attn-scale 0.00390625
