#!/bin/bash
# =============================================================================
# submit_pipeline.slurm
# Master job: runs on a lightweight general node and fans out per-rule jobs.
# Only dlc_inference lands on the GPU partition (via cluster.yaml).
# =============================================================================
#SBATCH --job-name=snakemake_master
#SBATCH --output=logs/snakemake_master_%j.out
#SBATCH --error=logs/snakemake_master_%j.err
#SBATCH --time=48:00:00
#SBATCH --partition=general
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --account=r01704

# =============================================================================
# 0. Setup
# =============================================================================
module load conda/25.3.0
conda activate icmh-dlc-310

cd /N/project/msk_dl/icmh-dlc-final-scripts/workflow
mkdir -p logs

# =============================================================================
# 1. Job submission function  (replaces cluster_submit.sh)
# Called once per rule job by Snakemake via --cluster.
# Args: partition account cpus mem time gpus jobscript
# =============================================================================
_submit_job() {
  local PARTITION=$1
  local ACCOUNT=$2
  local CPUS=$3
  local MEM=$4
  local TIME=$5
  local GPUS=$6
  local JOBSCRIPT=$7

  SBATCH_ARGS=(
    --partition="$PARTITION"
    --account="$ACCOUNT"
    --cpus-per-task="$CPUS"
    --mem="$MEM"
    --time="$TIME"
    --output="logs/slurm_%j.out"
    --error="logs/slurm_%j.err"
    --export=ALL
  )

  if [ "$GPUS" != "0" ]; then
    SBATCH_ARGS+=(--gpus-per-node="$GPUS")
  fi

  sbatch "${SBATCH_ARGS[@]}" "$JOBSCRIPT"
}
export -f _submit_job

# =============================================================================
# 2. Run Snakemake
# =============================================================================
snakemake \
  --cluster-config ../workflow/cluster.yaml \
  --cluster "bash -c '_submit_job \
    {cluster.partition} \
    {cluster.account} \
    {cluster.cpus} \
    {cluster.mem} \
    {cluster.time} \
    {cluster.gpus} \
    {jobscript}'" \
  --jobs 10 \
  --use-conda \
  --conda-prefix /N/project/msk_dl/conda-envs \
  --latency-wait 120 \
  --rerun-incomplete \
  --printshellcmds