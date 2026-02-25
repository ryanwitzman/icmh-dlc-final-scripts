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

# Make sure logs dir exists
mkdir -p logs

# ── Snakemake (submits GPU jobs as child SLURM jobs) ──────────────────────────
snakemake \
  --cluster "sbatch --partition={resources.partition} \
                    --account=r01704 \
                    --gpus-per-node={resources.gpus} \
                    --mem={resources.mem_mb}M \
                    --time={resources.runtime} \
                    --cpus-per-task={threads} \
                    --output=logs/slurm_%j.out \
                    --error=logs/slurm_%j.err" \
  --jobs 10 \
  --use-conda \
  --conda-prefix /N/project/msk_dl/conda-envs \
  --default-resources "partition='gpu'" gpus=1 mem_mb=16000 runtime=120 \
  --latency-wait 120 \
  --rerun-incomplete \
  --printshellcmds