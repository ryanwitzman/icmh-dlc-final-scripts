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
DLC_RESULTS_DIR="${PROJECT_BASE_DIR}/outputs/dlc_results/${BATCH_ID}"

# Use associative array to deduplicate videos, keeping only the latest version (since glob sorts alphabetically)
declare -A LATEST_VIDEOS
for video in "${PROJECT_BASE_DIR}/outputs/trimmed_resized/"*/*.mp4; do
    [ -e "$video" ] || continue
    filename=$(basename -- "$video")
    vid_stem="${filename%.*}"
    stem_no_prefix="${vid_stem#trimmed_}"
    LATEST_VIDEOS["$stem_no_prefix"]="$video"
done

for stem in "${!LATEST_VIDEOS[@]}"; do
    video="${LATEST_VIDEOS[$stem]}"
    echo "Running inference on $video..."
    python src/dlc/run_dlc_inference.py \
        --videos "$video" \
        --out_dir "$DLC_RESULTS_DIR" \
        --out_h5 "${DLC_RESULTS_DIR}/${stem}_superanimal.h5" \
        --superanimal superanimal_topviewmouse
done
