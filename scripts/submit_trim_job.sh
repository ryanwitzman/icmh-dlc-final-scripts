#!/bin/bash
#SBATCH --job-name=trim_videos
BASE_DIR=$(python -c "import yaml; print(yaml.safe_load(open('configs/config.yaml'))['base_dir'])")

#SBATCH --output=${BASE_DIR}/logs/trim_videos_%j.out
#SBATCH --error=${BASE_DIR}/logs/trim_videos_%j.err

#SBATCH --time=02:00:00
#SBATCH --partition=general
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --account=r01704

module load conda/25.3.0
source activate icmh-dlc-310

cd ${BASE_DIR}
python src/preprocess/batch_trim.py
