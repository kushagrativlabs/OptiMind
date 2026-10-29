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
profile="${IMAGE_GENERATION_PROFILE:-fast}"
case "${profile}" in
  fast)
    default_model_path="${models_dir}/lcm-ssd-1b.q4_k.gguf"
    default_vae_path="${models_dir}/sdxl_vae.safetensors"
    default_steps=4
    default_cfg=1.0
    default_sampler=lcm
    ;;
  sd15)
    default_model_path="${models_dir}/stable-diffusion-v1-5-pruned-emaonly-Q4_0.gguf"
    default_vae_path="${models_dir}/vae-ft-mse-840000-ema-pruned.safetensors"
    default_steps=12
    default_cfg=7.5
    default_sampler=euler_a
    ;;
  custom)
    : "${IMAGE_GENERATION_MODEL_PATH:?Set IMAGE_GENERATION_MODEL_PATH for the custom profile}"
    default_model_path="${IMAGE_GENERATION_MODEL_PATH}"
    default_vae_path="${IMAGE_GENERATION_VAE_PATH:-${models_dir}/sdxl_vae.safetensors}"
    default_steps=4
    default_cfg=1.0
    default_sampler=lcm
    ;;
  *)
    echo "Unknown image profile '${profile}'. Use: fast, sd15, or custom."
    exit 1
    ;;
esac
model_path="${IMAGE_GENERATION_MODEL_PATH:-${default_model_path}}"
vae_path="${IMAGE_GENERATION_VAE_PATH:-${default_vae_path}}"
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
  --steps "${IMAGE_GENERATION_STEPS:-${default_steps}}" \
  --cfg-scale "${IMAGE_GENERATION_CFG_SCALE:-${default_cfg}}" \
  --sampling-method "${IMAGE_GENERATION_SAMPLER:-${default_sampler}}" \
  --linear-scale 0.00390625 \
  --attn-scale 0.00390625
