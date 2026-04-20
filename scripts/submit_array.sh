#!/bin/bash

# ==========================================
# 1. ABSOLUTE PATHS (Bulletproof for Slurm)
# ==========================================
# Hardcoding the exact path so Slurm can never get confused again
PROJECT_DIR="/N/project/msk_dl/icmh-dlc-final-scripts"
STAGING_DIR="${PROJECT_DIR}/staging"
OUTPUT_DIR="${PROJECT_DIR}/outputs"
WORKFLOW_DIR="${PROJECT_DIR}/workflow"
CONFIG_FILE="${PROJECT_DIR}/configs/config.yaml"

# Get the BATCH_ID from config.yaml safely using the absolute path
export BATCH_ID=$(python3 -c "import yaml; print(yaml.safe_load(open('${CONFIG_FILE}'))['batch_id'])")

# ==========================================
# 2. MASTER SUBMISSION BLOCK (Runs on Login Node)
# ==========================================
if [ -z "$SLURM_JOB_ID" ]; then
    echo "Analyzing staging directory recursively: $STAGING_DIR"
    
    # Use find to recursively search for mp4 files and sort them alphabetically
    mapfile -t VIDEOS < <(find "$STAGING_DIR" -type f -iname "*.mp4" | sort)
    NUM_VIDEOS=${#VIDEOS[@]}

    if [ "$NUM_VIDEOS" -eq 0 ]; then
        echo "Error: No .mp4 files found recursively in $STAGING_DIR"
        exit 1
    fi

    ARRAY_MAX=$((NUM_VIDEOS - 1))
    echo "Found $NUM_VIDEOS videos. Submitting Slurm array 0-$ARRAY_MAX%1..."

    mkdir -p "${PROJECT_DIR}/logs"

    # Submit the array to the GPU partition
    sbatch \
        --job-name=dlc_array \
        --output="${PROJECT_DIR}/logs/dlc_array_%A_%a.out" \
        --error="${PROJECT_DIR}/logs/dlc_array_%A_%a.err" \
        --time=04:00:00 \
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

# Use the exact same find command so the array indices match perfectly
mapfile -t VIDEOS < <(find "$STAGING_DIR" -type f -iname "*.mp4" | sort)
CURRENT_FILE="${VIDEOS[$SLURM_ARRAY_TASK_ID]}"
BASENAME=$(basename "$CURRENT_FILE")
VID_NAME="${BASENAME%.*}"

echo "========================================"
echo "Processing Task ID: $SLURM_ARRAY_TASK_ID"
echo "Video: $VID_NAME"
echo "Batch ID: $BATCH_ID"
echo "========================================"

# Force the script to cd directly into the workflow directory
# This ensures Snakemake's relative path "../configs/config.yaml" works perfectly
cd "$WORKFLOW_DIR"

# Define the absolute path to the final output file for THIS video
TARGET_FILE="../outputs/qc/${BATCH_ID}/${VID_NAME}/${VID_NAME}_stats.csv"

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