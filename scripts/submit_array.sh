#!/bin/bash

# ==========================================
# 1. ABSOLUTE PATHS (Bulletproof for Slurm)
# ==========================================
PROJECT_DIR="/N/project/msk_dl/icmh-dlc-final-scripts"
STAGING_DIR="${PROJECT_DIR}/staging"
OUTPUT_DIR="${PROJECT_DIR}/outputs"
WORKFLOW_DIR="${PROJECT_DIR}/workflow"
CONFIG_FILE="${PROJECT_DIR}/configs/config.yaml"

export BATCH_ID=$(python3 -c "import yaml; print(yaml.safe_load(open('${CONFIG_FILE}'))['batch_id'])")

# ==========================================
# 2. MASTER SUBMISSION BLOCK (Runs on Login Node)
# ==========================================
if [ -z "$SLURM_JOB_ID" ]; then
    echo "Analyzing staging directory for missing outputs: $STAGING_DIR"
    mkdir -p "${PROJECT_DIR}/logs"

    # Define a tracking file for tasks that actually need processing
    PENDING_TASKS="${PROJECT_DIR}/logs/pending_tasks_${BATCH_ID}.txt"
    > "$PENDING_TASKS" # Clear or create the file

    # 1. Find all MP4s, completely ignoring any files containing '.trimmed'
    mapfile -t ALL_VIDEOS < <(find "$STAGING_DIR" -type f -iname "*.mp4" | grep -vi "\.trimmed" | sort)

    # Dictionary to keep track of duplicates
    declare -A SEEN_VIDEOS

    for filepath in "${ALL_VIDEOS[@]}"; do
        BASENAME=$(basename "$filepath")
        VID_NAME="${BASENAME%.*}"

        # 2. Prevent duplicate staging files from triggering multiple runs
        if [[ -n "${SEEN_VIDEOS[$VID_NAME]}" ]]; then
            continue
        fi
        SEEN_VIDEOS[$VID_NAME]=1

        # 3. Check if the final target already exists for this batch
        TARGET_FILE="${OUTPUT_DIR}/qc/${BATCH_ID}/${VID_NAME}/${VID_NAME}_stats.csv"

        if [[ ! -f "$TARGET_FILE" ]]; then
            # Needs processing, write the exact absolute path to the list
            echo "$filepath" >> "$PENDING_TASKS"
        fi
    done

    # Count how many videos actually need processing
    NUM_PENDING=$(wc -l < "$PENDING_TASKS")

    if [ "$NUM_PENDING" -eq 0 ]; then
        echo "Success: All final targets already exist! Nothing to run."
        rm -f "$PENDING_TASKS"
        exit 0
    fi

    # Adjust to 1-based indexing so it aligns with sed line numbers
    echo "Found $NUM_PENDING videos that need processing. Submitting Slurm array 1-$NUM_PENDING%1..."

    sbatch \
        --job-name=dlc_array \
        --output="${PROJECT_DIR}/logs/dlc_array_%A_%a.out" \
        --error="${PROJECT_DIR}/logs/dlc_array_%A_%a.err" \
        --time=02:30:00 \
        --partition=gpu-interactive \
        --account=r01704 \
        --cpus-per-task=4 \
        --mem=16G \
        --gpus=1 \
        --array=1-${NUM_PENDING}%1 \
        "$0" "$@"
    exit $?
fi

# ==========================================
# 3. ARRAY TASK EXECUTION BLOCK (Runs on Compute Node)
# ==========================================
set -x

module load conda/25.3.0
source activate icmh-dlc-310

# Read this specific worker's file path from the pending tasks list
PENDING_TASKS="${PROJECT_DIR}/logs/pending_tasks_${BATCH_ID}.txt"
CURRENT_FILE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$PENDING_TASKS")

BASENAME=$(basename "$CURRENT_FILE")
VID_NAME="${BASENAME%.*}"

echo "========================================"
echo "Processing Task ID: $SLURM_ARRAY_TASK_ID"
echo "Video: $VID_NAME"
echo "Batch ID: $BATCH_ID"
echo "========================================"

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