#!/bin/bash

if [ -z "$SLURM_JOB_ID" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
    ROOT_DIR="$(dirname "$SCRIPT_DIR")"
    export PROJECT_CONFIG_PATH="$ROOT_DIR/configs/config.yaml"
    export PROJECT_BASE_DIR=$(python -c "import yaml, os; print(os.path.abspath(os.path.join('${ROOT_DIR}', yaml.safe_load(open('${PROJECT_CONFIG_PATH}'))['base_dir'])))")
    
    echo "Submitting dlc_inference job to SLURM with logs at ${PROJECT_BASE_DIR}/logs/"
    sbatch \
        --job-name=dlc_inference \
        --output="${PROJECT_BASE_DIR}/logs/dlc_inference_%j.out" \
        --error="${PROJECT_BASE_DIR}/logs/dlc_inference_%j.err" \
        --time=01:00:00 \
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

BATCH_ID=$(python -c "
import yaml
from datetime import datetime
bid = yaml.safe_load(open(os.environ['PROJECT_CONFIG_PATH'])).get('batch_id', 'auto')
print(datetime.now().strftime('batch_%Y%m%d_%H%M%S') if bid == 'auto' else bid)
")
echo "Batch ID: ${BATCH_ID}"

BATCH_DIR="${PROJECT_BASE_DIR}/outputs/${BATCH_ID}"

for video in ${BATCH_DIR}/trimmed_resized/*.mp4; do
    filename=$(basename -- "$video")
    vid_stem="${filename%.*}"
    stem_no_prefix="${vid_stem#trimmed_}"

    echo "Running inference on $video..."
    python src/dlc/run_dlc_inference.py \
        --videos "$video" \
        --out_dir "${BATCH_DIR}/dlc_results" \
        --out_h5 "${BATCH_DIR}/dlc_results/${stem_no_prefix}_superanimal.h5" \
        --superanimal superanimal_topviewmouse
done
