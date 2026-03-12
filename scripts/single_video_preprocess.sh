#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_PATH="$ROOT_DIR/configs/config.yaml"

BASE_DIR=$(python -c "import yaml, os; print(os.path.abspath(os.path.join('${ROOT_DIR}', yaml.safe_load(open('${CONFIG_PATH}'))['base_dir'])))")
cd "${BASE_DIR}"
python src/preprocess/trim_video.py --input-file "${BASE_DIR}/staging/CR_D4_3-11-24_SP_RM1.MP4"