#!/bin/bash
#SBATCH --job-name=snakemake_master
BASE_DIR=$(python -c "import yaml; print(yaml.safe_load(open('configs/config.yaml'))['base_dir'])")

#SBATCH --output=${BASE_DIR}/logs/snakemake_master_%j.out
#SBATCH --error=${BASE_DIR}/logs/snakemake_master_%j.err
#SBATCH --time=01:00:00
#SBATCH --partition=general
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --account=r01704

exec > ${BASE_DIR}/workflow/master_debug.log 2>&1
set -x

module load conda/25.3.0
source activate icmh-dlc-310

cd ${BASE_DIR}/workflow
snakemake --unlock

mkdir -p logs

snakemake \
  --cluster-config cluster.yaml \
  --cluster "./.slurm_submit_wrapper.sh {cluster.partition} {cluster.account} {cluster.cpus} {cluster.mem} {cluster.time} {cluster.gpus}" \
  --jobs 10 \
  --use-conda \
  --conda-prefix /N/project/msk_dl/conda-envs \
  --latency-wait 120 \
  --rerun-incomplete \
  --rerun-triggers mtime \
  --printshellcmds