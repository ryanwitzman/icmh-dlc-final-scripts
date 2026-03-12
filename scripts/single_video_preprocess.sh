#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_PATH="$ROOT_DIR/configs/config.yaml"

BASE_DIR=$(python -c "import yaml; print(yaml.safe_load(open('${CONFIG_PATH}'))['base_dir'])")
cd "${BASE_DIR}"

python src/preprocess/trim_video.py --input-file "${BASE_DIR}/inputs/CR_D4_3-11-24_SP_RM1.MP4"