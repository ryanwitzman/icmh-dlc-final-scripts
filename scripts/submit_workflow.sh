#!/bin/bash
#SBATCH --job-name=snakemake_master
#SBATCH --output=logs/snakemake_master_%j.out
#SBATCH --error=logs/snakemake_master_%j.err
#SBATCH --time=48:00:00
#SBATCH --partition=general         # master job just orchestrates, no GPU needed
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --account=r01704

# ── Environment ──────────────────────────────────────────────────────────────
module load conda/25.3.0
conda activate icmh-dlc-310

# ── Working directory ─────────────────────────────────────────────────────────
cd /N/project/msk_dl/icmh-dlc-final-scripts/workflow


# ── Snakemake (submits GPU jobs as child SLURM jobs) ──────────────────────────
snakemake \
  --executor slurm \
  --jobs 10 \
  --use-conda \
  --conda-prefix /N/project/msk_dl/conda-envs \
  --default-resources \
      slurm_partition="gpu" \
      slurm_account="r01704" \
      slurm_extra="'--gpus-per-node=1'" \
      mem_mb=16000 \
      runtime=120 \
  --latency-wait 120 \
  --rerun-incomplete \
  --printshellcmds