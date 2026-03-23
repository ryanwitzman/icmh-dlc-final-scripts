#!/bin/bash
PARTITION=$1
ACCOUNT=$2
CPUS=$3
MEM=$4
TIME=$5
GPUS=$6
JOBSCRIPT=$7

BASE_DIR=$(python3 -c "import yaml; print(yaml.safe_load(open('../configs/config.yaml'))['base_dir'])")

SBATCH_ARGS=(
  --partition="$PARTITION"
  --account="$ACCOUNT"
  --cpus-per-task="$CPUS"
  --mem="$MEM"
  --time="$TIME"
  --output="${BASE_DIR}/logs/slurm_%j.out"
  --error="${BASE_DIR}/logs/slurm_%j.err"
  --export=ALL
)

if [ "$GPUS" != "0" ]; then
  SBATCH_ARGS+=(--gpus-per-node="$GPUS")
fi

sbatch "${SBATCH_ARGS[@]}" "$JOBSCRIPT"