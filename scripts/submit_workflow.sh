#!/bin/bash
#SBATCH --job-name=snakemake_master
#SBATCH --output=logs/snakemake_master_%j.out
#SBATCH --error=logs/snakemake_master_%j.err
#SBATCH --time=48:00:00
#SBATCH --partition=standard 
#SBATCH --ntasks=1
#SBATCH --mem=4G

# Load your environment (Conda or Container)
# e.g., module load miniconda3
# source activate dlc_env

# Run Snakemake and tell it to use Slurm for its jobs
# It maps the resources (gpus, mem_mb, time) defined in your rules to Slurm SBATCH arguments.
snakemake --executor slurm \
          --jobs 10 \
          --use-conda \
          --default-resources slurm_partition="gpu" slurm_account="r01704" \
          --latency-wait 60