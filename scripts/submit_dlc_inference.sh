#!/bin/bash
if [ -z "$SLURM_JOB_ID" ]; then
    BASE_DIR=$(python -c "import yaml; print(yaml.safe_load(open('configs/config.yaml'))['base_dir'])")
    
    echo "Submitting dlc_inference job to SLURM with logs at ${BASE_DIR}/logs/"
    sbatch \
        --job-name=dlc_inference \
        --output="${BASE_DIR}/logs/dlc_inference_%j.out" \
        --error="${BASE_DIR}/logs/dlc_inference_%j.err" \
        --time=01:00:00 \
        --partition=gpu \
        --gpus=1 \
        --mem=16G \
        --account=r01704 \
        "$0" "$@"
    exit $?
fi

module load conda/25.3.0
source activate icmh-dlc-310

BASE_DIR=$(python -c "import yaml; print(yaml.safe_load(open('configs/config.yaml'))['base_dir'])")
cd ${BASE_DIR}

BATCH_ID=$(python -c "
import yaml
from datetime import datetime
bid = yaml.safe_load(open('configs/config.yaml')).get('batch_id', 'auto')
print(datetime.now().strftime('batch_%Y%m%d_%H%M%S') if bid == 'auto' else bid)
")
echo "Batch ID: ${BATCH_ID}"

BATCH_DIR="${BASE_DIR}/outputs/${BATCH_ID}"

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
