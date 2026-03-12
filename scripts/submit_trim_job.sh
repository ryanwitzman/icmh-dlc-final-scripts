#!/bin/bash

if [ -z "$SLURM_JOB_ID" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
    ROOT_DIR="$(dirname "$SCRIPT_DIR")"
    export PROJECT_CONFIG_PATH="$ROOT_DIR/configs/config.yaml"
    export PROJECT_BASE_DIR=$(python -c "import yaml, os; print(os.path.abspath(os.path.join('${ROOT_DIR}', yaml.safe_load(open('${PROJECT_CONFIG_PATH}'))['base_dir'])))")
    
    echo "Submitting trim_videos job to SLURM with logs at ${PROJECT_BASE_DIR}/logs/"
    sbatch \
        --job-name=trim_videos \
        --output="${PROJECT_BASE_DIR}/logs/trim_videos_%j.out" \
        --error="${PROJECT_BASE_DIR}/logs/trim_videos_%j.err" \
        --time=00:30:00 \
        --partition=gpu-interactive \
        --ntasks=1 \
        --cpus-per-task=1 \
        --mem=16G \
        --account=r01704 \
        "$0" "$@"
    exit $?
fi

module load conda/25.3.0
source activate icmh-dlc-310

cd "${PROJECT_BASE_DIR}"

python src/preprocess/batch_trim.py
