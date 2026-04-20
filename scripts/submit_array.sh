#!/bin/bash

# ==========================================
# 1. PATH & CONFIGURATION PARSING
# ==========================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
export PROJECT_CONFIG_PATH="$ROOT_DIR/configs/config.yaml"

# Parse paths dynamically from config.yaml
export PROJECT_BASE_DIR=$(python3 -c "import yaml, os; config=yaml.safe_load(open('${PROJECT_CONFIG_PATH}')); print(os.path.abspath(os.path.join('${ROOT_DIR}', config.get('base_dir', ''))))")
export STAGING_DIR=$(python3 -c "import yaml, os; config=yaml.safe_load(open('${PROJECT_CONFIG_PATH}')); print(os.path.abspath(os.path.join('${ROOT_DIR}', config.get('staging_dir', '../staging'))))")
export OUTPUT_DIR=$(python3 -c "import yaml, os; config=yaml.safe_load(open('${PROJECT_CONFIG_PATH}')); print(os.path.abspath(os.path.join('${ROOT_DIR}', config.get('output_dir', '../outputs'))))")
export BATCH_ID=$(python3 -c "import yaml; config=yaml.safe_load(open('${PROJECT_CONFIG_PATH}')); print(config.get('batch_id', 'batch_default'))")

# ==========================================
# 2. MASTER SUBMISSION BLOCK (Runs on Login Node)
# ==========================================
if [ -z "$SLURM_JOB_ID" ]; then
    echo "Analyzing staging directory: $STAGING_DIR"
    
    # Count how many .mp4 files are in the staging directory
    VIDEOS=("$STAGING_DIR"/*.mp4)
    NUM_VIDEOS=${#VIDEOS[@]}

    if [ "$NUM_VIDEOS" -eq 0 ] || [ ! -e "${VIDEOS[0]}" ]; then
        echo "Error: No .mp4 files found in $STAGING_DIR"
        exit 1
    fi

    ARRAY_MAX=$((NUM_VIDEOS - 1))
    echo "Found $NUM_VIDEOS videos. Submitting Slurm array 0-$ARRAY_MAX%1..."

    mkdir -p "${PROJECT_BASE_DIR}/logs"

    # Submit the array to the GPU partition
    sbatch \
        --job-name=dlc_array \
        --output="${PROJECT_BASE_DIR}/logs/dlc_array_%A_%a.out" \
        --error="${PROJECT_BASE_DIR}/logs/dlc_array_%A_%a.err" \
        --time=02:30:00 \
        --partition=gpu \
        --account=r01704 \
        --cpus-per-task=4 \
        --mem=16G \
        --gpus=1 \
        --array=0-${ARRAY_MAX}%1 \
        "$0" "$@"
    exit $?
fi

# ==========================================
# 3. ARRAY TASK EXECUTION BLOCK (Runs on Compute Node)
# ==========================================
set -x

module load conda/25.3.0
source activate icmh-dlc-310

# Map this specific Slurm array task ID to a specific video
VIDEOS=("$STAGING_DIR"/*.mp4)
CURRENT_FILE="${VIDEOS[$SLURM_ARRAY_TASK_ID]}"
BASENAME=$(basename "$CURRENT_FILE")
VID_NAME="${BASENAME%.*}"

echo "========================================"
echo "Processing Task ID: $SLURM_ARRAY_TASK_ID"
echo "Video: $VID_NAME"
echo "Batch ID: $BATCH_ID"
echo "========================================"

cd "${PROJECT_BASE_DIR}/workflow"

# Define the absolute path to the final output file for THIS video
TARGET_FILE="${OUTPUT_DIR}/qc/${BATCH_ID}/${VID_NAME}/${VID_NAME}_stats.csv"

# Unlock the directory safely (in case a previous crash left a lock)
snakemake --unlock --cores 1

# Run snakemake requesting ONLY the target file for this video
snakemake \
  --cores 4 \
  --use-conda \
  --conda-prefix /N/project/msk_dl/conda-envs \
  --rerun-incomplete \
  --printshellcmds \
  "$TARGET_FILE"