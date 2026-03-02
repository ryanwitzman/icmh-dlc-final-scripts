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
# 1. Create a dedicated SLURM submit wrapper
# This avoids the "jobscript" NameError and export -f subshell scoping issues.
# Snakemake automatically appends the job script path as the final argument ($7).
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
# Notice {jobscript} is intentionally omitted here.
snakemake \
  --cluster-config ../workflow/cluster.yaml \
  --cluster "./.slurm_submit_wrapper.sh {cluster.partition} {cluster.account} {cluster.cpus} {cluster.mem} {cluster.time} {cluster.gpus}" \
  --jobs 10 \
  --use-conda \
  --conda-prefix /N/project/msk_dl/conda-envs \
  --latency-wait 120 \
  --rerun-incomplete \
  --printshellcmds