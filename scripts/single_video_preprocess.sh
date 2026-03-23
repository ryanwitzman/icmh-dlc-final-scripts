#!/bin/bash

if [ -z "$SLURM_JOB_ID" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
    ROOT_DIR="$(dirname "$SCRIPT_DIR")"
    export PROJECT_CONFIG_PATH="$ROOT_DIR/configs/config.yaml"
    export PROJECT_BASE_DIR=$(python3 -c "import yaml, os; print(os.path.abspath(os.path.join('${ROOT_DIR}', yaml.safe_load(open('${PROJECT_CONFIG_PATH}'))['base_dir'])))")

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

module load conda/25.3.0
source activate icmh-dlc-310

cd "${PROJECT_BASE_DIR}"

BATCH_ID=$(python3 -c "
import yaml, os
from datetime import datetime
bid = yaml.safe_load(open(os.environ['PROJECT_CONFIG_PATH'])).get('batch_id', 'auto')
print(datetime.now().strftime('batch_%Y%m%d_%H%M%S') if bid == 'auto' else bid)
")

RESIZE_SCALE=$(python3 -c "
import yaml, os
print(yaml.safe_load(open(os.environ['PROJECT_CONFIG_PATH'])).get('resize_scale', 'iw/2:ih/2'))
")

LOG_DIR="${PROJECT_BASE_DIR}/outputs/logs/${BATCH_ID}"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/trim_video_log.txt"

log() {
    local msg="$1"
    local line="[$(date '+%Y-%m-%d %H:%M:%S')] $msg"
    echo "$line" | tee -a "$LOG_FILE"
}

{
    echo ""
    echo "--- Batch Run: $(date '+%Y-%m-%d %H:%M:%S') ---"
} | tee -a "$LOG_FILE"

INPUT_FILE="${PROJECT_BASE_DIR}/staging/CR_D4_3-11-24_SP_RM1.MP4"
FILENAME=$(basename -- "$INPUT_FILE")
STEM="${FILENAME%.*}"
EXT="mp4"

SRC_MB=$(python3 -c "import os; print(f'{os.path.getsize(\"${INPUT_FILE}\") / 1e6:.1f}')" 2>/dev/null || echo "?.?")

TRIMMED_FILE="${PROJECT_BASE_DIR}/outputs/trimmed/${BATCH_ID}/trimmed_${STEM}.${EXT}"
RESIZED_FILE="${PROJECT_BASE_DIR}/outputs/resized/${BATCH_ID}/trimmed_${STEM}.${EXT}"

EXISTING_TRIM=$(ls "${PROJECT_BASE_DIR}/outputs/trimmed/"*"/trimmed_${STEM}.${EXT}" 2>/dev/null | head -n 1)
if [ -n "$EXISTING_TRIM" ]; then
    log "${FILENAME} (src=${SRC_MB}MB) [TRIM]: SKIPPED | previously trimmed at ${EXISTING_TRIM}"
    TRIMMED_FILE="$EXISTING_TRIM"
else
    mkdir -p "$(dirname "$TRIMMED_FILE")"
    log "${FILENAME} (src=${SRC_MB}MB) [TRIM]: STARTING | output -> ${TRIMMED_FILE}"
    python3 src/preprocess/trim_video.py \
        --input-file "$INPUT_FILE" \
        --output-file "$TRIMMED_FILE"
    if [ $? -ne 0 ] || [ ! -f "$TRIMMED_FILE" ]; then
        log "${FILENAME} (src=${SRC_MB}MB) [TRIM]: ERROR | failed, aborting"
        exit 1
    fi
    log "${FILENAME} (src=${SRC_MB}MB) [TRIM]: DONE | ${TRIMMED_FILE}"
fi

EXISTING_RESIZE=$(ls "${PROJECT_BASE_DIR}/outputs/resized/"*"/trimmed_${STEM}.${EXT}" 2>/dev/null | head -n 1)
if [ -n "$EXISTING_RESIZE" ]; then
    log "${FILENAME} (src=${SRC_MB}MB) [RESIZE]: SKIPPED | previously resized at ${EXISTING_RESIZE}"
else
    mkdir -p "$(dirname "$RESIZED_FILE")"
    log "${FILENAME} (src=${SRC_MB}MB) [RESIZE]: STARTING | output -> ${RESIZED_FILE}"
    ffmpeg -y \
        -i "$TRIMMED_FILE" \
        -vf "scale=${RESIZE_SCALE}" \
        -c:v libx264 -crf 18 -preset fast \
        -an \
        "$RESIZED_FILE"
    if [ $? -ne 0 ] || [ ! -f "$RESIZED_FILE" ]; then
        log "${FILENAME} (src=${SRC_MB}MB) [RESIZE]: ERROR | failed, aborting"
        exit 1
    fi
    log "${FILENAME} (src=${SRC_MB}MB) [RESIZE]: DONE | ${RESIZED_FILE}"
fi