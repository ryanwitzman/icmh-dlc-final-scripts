#!/bin/bash
PARTITION=$1
ACCOUNT=$2
CPUS=$3
MEM=$4
TIME=$5
GPUS=$6
JOBSCRIPT=$7

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
