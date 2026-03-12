#!/bin/bash
if [ -z "$SLURM_JOB_ID" ]; then
    BASE_DIR=$(python -c "import yaml; print(yaml.safe_load(open('configs/config.yaml'))['base_dir'])")
    
    echo "Submitting snakemake_master job to SLURM with logs at ${BASE_DIR}/logs/"
    sbatch \
        --job-name=snakemake_master \
        --output="${BASE_DIR}/logs/snakemake_master_%j.out" \
        --error="${BASE_DIR}/logs/snakemake_master_%j.err" \
        --time=02:00:00 \
        --partition=general \
        --ntasks=1 \
        --cpus-per-task=1 \
        --mem=4G \
        --account=r01704 \
        "$0" "$@"
    exit $?
fi

BASE_DIR=$(python -c "import yaml; print(yaml.safe_load(open('configs/config.yaml'))['base_dir'])")

exec > ${BASE_DIR}/workflow/master_debug.log 2>&1
set -x

module load conda/25.3.0
source activate icmh-dlc-310

cd ${BASE_DIR}/workflow
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