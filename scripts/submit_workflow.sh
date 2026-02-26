#!/bin/bash
#SBATCH --job-name=snakemake_master
#SBATCH --output=logs/snakemake_master_%j.out
#SBATCH --error=logs/snakemake_master_%j.err
#SBATCH --time=48:00:00
#SBATCH --partition=general
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --account=r01704

module load conda/25.3.0
conda activate icmh-dlc-310

cd /N/project/msk_dl/icmh-dlc-final-scripts/workflow
mkdir -p logs

snakemake \
  --cluster "sbatch \
    --partition=gpu \
    --account=r01704 \
    --gpus-per-node=1 \
    --mem=16G \
    --time=04:00:00 \
    --cpus-per-task=4 \
    --output=logs/slurm_%j.out \
    --error=logs/slurm_%j.err \
    --wrap='module load cudatoolkit/11.8; \
            module load conda/25.3.0; \
            conda activate icmh-dlc-310; \
            export LD_LIBRARY_PATH=/N/u/rwitzman/Quartz/.conda/envs/icmh-dlc-310/lib:\$LD_LIBRARY_PATH; \
            {cmd}'" \
  --jobs 10 \
  --use-conda \
  --conda-prefix /N/project/msk_dl/conda-envs \
  --latency-wait 120 \
  --rerun-incomplete \
  --printshellcmds