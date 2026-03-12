#!/bin/bash
if [ -z "$SLURM_JOB_ID" ]; then
    BASE_DIR=$(python -c "import yaml; print(yaml.safe_load(open('configs/config.yaml'))['base_dir'])")
    
    echo "Submitting trim_videos job to SLURM with logs at ${BASE_DIR}/logs/"
    sbatch \
        --job-name=trim_videos \
        --output="${BASE_DIR}/logs/trim_videos_%j.out" \
        --error="${BASE_DIR}/logs/trim_videos_%j.err" \
        --time=00:30:00 \
        --partition=gpu \
        --ntasks=1 \
        --cpus-per-task=1 \
        --mem=16G \
        --account=r01704 \
        "$0" "$@"
    exit $?
fi

module load conda/25.3.0
source activate icmh-dlc-310

BASE_DIR=$(python -c "import yaml; print(yaml.safe_load(open('configs/config.yaml'))['base_dir'])")
cd ${BASE_DIR}

python src/preprocess/batch_trim.py
