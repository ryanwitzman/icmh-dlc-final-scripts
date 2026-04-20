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

    echo "Submitting DLC 30s Evaluation Pipeline to Quartz..."
    
    sbatch \
        --job-name=dlc_eval_30s \
        --output="${SLURM_LOG_DIR}/dlc_eval_%j.out" \
        --error="${SLURM_LOG_DIR}/dlc_eval_%j.err" \
        --time=03:00:00 \
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
exec > >(tee -a "${LOG_DIR}/dlc_eval_log.txt") 2>&1

echo "=== Job ${SLURM_JOB_ID} started on $(hostname) at $(date) ==="

echo "Loading environment..."
module load ffmpeg
module load conda/25.3.0
CONDA_BASE=$(conda info --base)
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate icmh-dlc-310

# Directory Setup
EVAL_DIR="${PROJECT_BASE_DIR}/outputs/evaluation_30s/${BATCH_ID}"
GT_VID_DIR="${EVAL_DIR}/videos/ground_truth"
TEST_VID_DIR="${EVAL_DIR}/videos/resized"
GT_RESULTS_DIR="${EVAL_DIR}/results/ground_truth"
TEST_RESULTS_DIR="${EVAL_DIR}/results/resized"
PLOTS_DIR="${EVAL_DIR}/plots"

mkdir -p "$GT_VID_DIR" "$TEST_VID_DIR" "$GT_RESULTS_DIR" "$TEST_RESULTS_DIR" "$PLOTS_DIR"

declare -A ALL_VIDEOS

# Collect resized videos to map back to trimmed ground truth
# Exclude *labeled.mp4 files so we don't accidentally run inference on DLC outputs
while IFS= read -r -d '' res_video; do
    filename=$(basename -- "$res_video")
    vid_stem="${filename%.*}"
    
    # Search for this exact filename anywhere inside outputs/trimmed/
    gt_video=$(find "${PROJECT_BASE_DIR}/outputs/trimmed/" -type f -name "$filename" | head -n 1)
    
    if [ -n "$gt_video" ] && [ -f "$gt_video" ]; then
        ALL_VIDEOS["$vid_stem"]="$res_video|$gt_video"
    else
        echo "WARNING: Ground truth video not found for $filename (searched inside outputs/trimmed/)"
    fi
done < <(find "${PROJECT_BASE_DIR}/outputs/resized/" -type f -name "*.mp4" ! -name "*labeled.mp4" -print0)

echo "Found ${#ALL_VIDEOS[@]} paired video(s) for evaluation."

if [ ${#ALL_VIDEOS[@]} -eq 0 ]; then
    echo "No valid video pairs found. Exiting."
    exit 0
fi

for stem in "${!ALL_VIDEOS[@]}"; do
    IFS='|' read -r res_video gt_video <<< "${ALL_VIDEOS[$stem]}"
    
    gt_30s="${GT_VID_DIR}/${stem}.mp4"
    res_30s="${TEST_VID_DIR}/${stem}.mp4"
    
    echo "----------------------------------------------------------------"
    echo "Processing: $stem"
    
    # 1. Extract first 30 seconds if not already done
    if [ ! -f "$gt_30s" ]; then
        echo "Extracting 30s ground truth clip..."
        ffmpeg -y -i "$gt_video" -t 30 -c:v copy -c:a copy "$gt_30s" -loglevel error
    fi
    
    if [ ! -f "$res_30s" ]; then
        echo "Extracting 30s resized clip..."
        ffmpeg -y -i "$res_video" -t 30 -c:v copy -c:a copy "$res_30s" -loglevel error
    fi
    
    # 2. Run Ground Truth Inference
    if [ ! -f "${GT_RESULTS_DIR}/${stem}_superanimal.h5" ]; then
        echo "Running DLC on Ground Truth (Full Res)..."
        python3 src/dlc/run_dlc_inference.py \
            --videos "$gt_30s" \
            --out_dir "$GT_RESULTS_DIR" \
            --batch_id "$BATCH_ID" \
            --out_h5 "${GT_RESULTS_DIR}/${stem}_superanimal.h5" \
            --superanimal superanimal_topviewmouse
    fi
    
    # 3. Run Test Inference (Resized)
    if [ ! -f "${TEST_RESULTS_DIR}/${stem}_superanimal.h5" ]; then
        echo "Running DLC on Resized Video..."
        python3 src/dlc/run_dlc_inference.py \
            --videos "$res_30s" \
            --out_dir "$TEST_RESULTS_DIR" \
            --batch_id "$BATCH_ID" \
            --out_h5 "${TEST_RESULTS_DIR}/${stem}_superanimal.h5" \
            --superanimal superanimal_topviewmouse
    fi
    
    # 4. Run Python Comparison Script
    echo "Generating graphical quality comparison..."
    python3 src/dlc/compare_dlc_resolution.py \
        --gt_h5 "${GT_RESULTS_DIR}/${stem}_superanimal.h5" \
        --test_h5 "${TEST_RESULTS_DIR}/${stem}_superanimal.h5" \
        --gt_vid "$gt_30s" \
        --test_vid "$res_30s" \
        --out_plot "${PLOTS_DIR}/${stem}_quality_comparison.png"
done

echo "=== Job ${SLURM_JOB_ID} finished at $(date) ==="