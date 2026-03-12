#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
export PROJECT_CONFIG_PATH="$ROOT_DIR/configs/config.yaml"
export PROJECT_BASE_DIR=$(python -c "import yaml, os; print(os.path.abspath(os.path.join('${ROOT_DIR}', yaml.safe_load(open('${PROJECT_CONFIG_PATH}'))['base_dir'])))")

if [ -z "$SLURM_JOB_ID" ]; then
    echo "Submitting trim_video job to SLURM with logs at ${PROJECT_BASE_DIR}/logs/"
    sbatch \
        --job-name=trim_video \
        --output="${PROJECT_BASE_DIR}/logs/trim_video_%j.out" \
        --error="${PROJECT_BASE_DIR}/logs/trim_video_%j.err" \
        --time=00:10:00 \
        --partition=gpu-interactive \
        --gpus=1 \
        --mem=16G \
        --account=r01704 \
        "$0" "$@"
    exit $?
fi

cd "${PROJECT_BASE_DIR}"
python src/preprocess/trim_video.py --input-file "${PROJECT_BASE_DIR}/staging/CR_D4_3-11-24_SP_RM1.MP4"