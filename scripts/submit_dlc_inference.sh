#!/bin/bash
#SBATCH --job-name=dlc_inference
BASE_DIR=$(python -c "import yaml; print(yaml.safe_load(open('configs/config.yaml'))['base_dir'])")

#SBATCH --output=${BASE_DIR}/logs/dlc_inference_%j.out
#SBATCH --error=${BASE_DIR}/logs/dlc_inference_%j.err
#SBATCH --time=04:00:00
#SBATCH --partition=gpu
#SBATCH --gpus=1
#SBATCH --mem=32G
#SBATCH --account=r01704

module load conda/25.3.0
source activate icmh-dlc-310

cd ${BASE_DIR}

for video in ${BASE_DIR}/outputs/trimmed_resized/*.mp4; do
    filename=$(basename -- "$video")
    vid_stem="${filename%.*}"
    stem_no_prefix="${vid_stem#trimmed_}"

    echo "Running inference on $video..."
    python src/dlc/run_dlc_inference.py \
        --videos "$video" \
        --out_dir "${BASE_DIR}/outputs/dlc_results" \
        --out_h5 "${BASE_DIR}/outputs/dlc_results/${stem_no_prefix}_superanimal.h5" \
        --superanimal superanimal_topviewmouse
done
