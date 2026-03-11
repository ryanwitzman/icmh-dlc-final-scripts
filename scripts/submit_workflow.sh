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

# =============================================================================
# EMERGENCY DEBUG TRAP (Must be below SBATCH headers)
# =============================================================================
exec > /N/project/msk_dl/icmh-dlc-final-scripts/workflow/master_debug.log 2>&1
set -x

# =============================================================================
# 0. Setup
# =============================================================================
module load conda/25.3.0
source activate icmh-dlc-310

cd /N/project/msk_dl/icmh-dlc-final-scripts/workflow
snakemake --unlock

mkdir -p logs

# =============================================================================
# 1. Create a dedicated SLURM submit wrapper
# =============================================================================
cat << 'EOF' > .slurm_submit_wrapper.sh
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
EOF

chmod +x .slurm_submit_wrapper.sh

# =============================================================================
# 2. Run Snakemake
# =============================================================================
# Changed cluster-config path slightly since we are already in the workflow dir
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