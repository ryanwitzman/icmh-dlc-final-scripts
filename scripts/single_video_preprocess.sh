#!/bin/bash
BASE_DIR=$(python -c "import yaml; print(yaml.safe_load(open('configs/config.yaml'))['base_dir'])")
cd ${BASE_DIR}

python src/preprocess/trim_video.py --input-file "${BASE_DIR}/inputs/CR_D4_3-11-24_SP_RM1.MP4"