#!/bin/bash

if [ -z "$SLURM_JOB_ID" ]; then
    SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]:-$0}")"
    SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
    ROOT_DIR="$(dirname "$SCRIPT_DIR")"
    PROJECT_CONFIG_PATH="$ROOT_DIR/configs/config.yaml"

    if [ ! -f "$PROJECT_CONFIG_PATH" ]; then
        echo "ERROR: Config not found at $PROJECT_CONFIG_PATH" >&2
        exit 1
    fi

    PROJECT_BASE_DIR=$(python3 -c "import yaml, os; print(os.path.abspath(os.path.join('${ROOT_DIR}', yaml.safe_load(open('${PROJECT_CONFIG_PATH}'))['base_dir'])))")
    BATCH_ID=$(python3 -c "import yaml, os; from datetime import datetime; bid = yaml.safe_load(open('${PROJECT_CONFIG_PATH}')).get('batch_id', 'auto'); print(datetime.now().strftime('batch_%Y%m%d_%H%M%S') if bid == 'auto' else bid)")

    SLURM_LOG_DIR="${PROJECT_BASE_DIR}/logs"
    mkdir -p "$SLURM_LOG_DIR"

    echo "Submitting dlc_inference to Quartz..."
    echo "  Base Dir: $PROJECT_BASE_DIR"
    echo "  Batch ID: $BATCH_ID"

    sbatch \
        --job-name=dlc_inference \
        --output="${SLURM_LOG_DIR}/dlc_inference_%j.out" \
        --error="${SLURM_LOG_DIR}/dlc_inference_%j.err" \
        --time=02:00:00 \
        --partition=gpu-interactive \
        --gpus=1 \
        --mem=32G \
        --account=r01704 \
        --export=ALL,PROJECT_CONFIG_PATH="${PROJECT_CONFIG_PATH}",PROJECT_BASE_DIR="${PROJECT_BASE_DIR}",BATCH_ID="${BATCH_ID}" \
        "$SCRIPT_PATH" "$@"
    exit $?
fi

set -eo pipefail

LOG_DIR="${PROJECT_BASE_DIR}/outputs/logs/${BATCH_ID}"
mkdir -p "$LOG_DIR"
exec > >(tee -a "${LOG_DIR}/dlc_inference_log.txt") 2>&1

echo "=== Job ${SLURM_JOB_ID} started on $(hostname) at $(date) ==="

echo "Loading environment..."
module load conda/25.3.0
CONDA_BASE=$(conda info --base)
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate icmh-dlc-310
echo "Active environment: $CONDA_DEFAULT_ENV"

cd "${PROJECT_BASE_DIR}"

DLC_RESULTS_DIR="${PROJECT_BASE_DIR}/outputs/dlc_results/${BATCH_ID}"
mkdir -p "$DLC_RESULTS_DIR"

declare -A ALL_VIDEOS
declare -A PENDING_VIDEOS

while IFS= read -r -d '' video; do
    filename=$(basename -- "$video")
    vid_stem="${filename%.*}"
    stem_no_prefix="${vid_stem#trimmed_}"
    ALL_VIDEOS["$stem_no_prefix"]="$video"
done < <(find "${PROJECT_BASE_DIR}/outputs/resized/" -type f -name "*.mp4" -print0)

echo "Found ${#ALL_VIDEOS[@]} total video(s) in resized folder."

for stem in "${!ALL_VIDEOS[@]}"; do
    video="${ALL_VIDEOS[$stem]}"
    
    EXISTING_H5=$(ls "${PROJECT_BASE_DIR}/outputs/dlc_results/"*/"${stem}_superanimal.h5" 2>/dev/null | head -n 1 || true)
    
    if [ -n "$EXISTING_H5" ] && [ -f "$EXISTING_H5" ]; then
        echo "  -> Skipping $stem (Inference complete at $EXISTING_H5)"
    else
        PENDING_VIDEOS["$stem"]="$video"
    fi
done

if [ ${#PENDING_VIDEOS[@]} -eq 0 ]; then
    echo "All videos have already been processed. Nothing to do!"
    echo "=== Job ${SLURM_JOB_ID} finished at $(date) ==="
    exit 0
fi

echo "Proceeding with inference on ${#PENDING_VIDEOS[@]} pending video(s)..."

for stem in "${!PENDING_VIDEOS[@]}"; do
    video="${PENDING_VIDEOS[$stem]}"
    
    echo "----------------------------------------------------------------"
    echo "Processing: $stem"
    echo "Source: $video"
    
    python3 src/dlc/run_dlc_inference.py \
        --videos "$video" \
        --out_dir "$DLC_RESULTS_DIR" \
        --batch_id "$BATCH_ID" \
        --out_h5 "${DLC_RESULTS_DIR}/${stem}_superanimal.h5" \
        --superanimal superanimal_topviewmouse
done

echo "=== Job ${SLURM_JOB_ID} finished at $(date) ==="