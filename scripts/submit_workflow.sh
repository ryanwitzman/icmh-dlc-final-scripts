#!/bin/bash
#SBATCH --job-name=snakemake_master
#SBATCH --output=/N/project/msk_dl/icmh-dlc-final-scripts/workflow/logs/snakemake_master_%j.out
#SBATCH --error=/N/project/msk_dl/icmh-dlc-final-scripts/workflow/logs/snakemake_master_%j.err
#SBATCH --time=01:00:00
#SBATCH --partition=general
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --account=r01704

exec > /N/project/msk_dl/icmh-dlc-final-scripts/workflow/master_debug.log 2>&1
set -x

module load conda/25.3.0
source activate icmh-dlc-310

cd /N/project/msk_dl/icmh-dlc-final-scripts/workflow
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