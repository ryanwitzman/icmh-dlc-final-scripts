#!/bin/bash

if [ -z "$SLURM_JOB_ID" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
    ROOT_DIR="$(dirname "$SCRIPT_DIR")"
    export PROJECT_CONFIG_PATH="$ROOT_DIR/configs/config.yaml"
    export PROJECT_BASE_DIR=$(python3 -c "import yaml, os; print(os.path.abspath(os.path.join('${ROOT_DIR}', yaml.safe_load(open('${PROJECT_CONFIG_PATH}'))['base_dir'])))")
    
    echo "Submitting snakemake_master job to SLURM with logs at ${PROJECT_BASE_DIR}/logs/"
    sbatch \
        --job-name=snakemake_master \
        --output="${PROJECT_BASE_DIR}/logs/snakemake_master_%j.out" \
        --error="${PROJECT_BASE_DIR}/logs/snakemake_master_%j.err" \
        --time=02:00:00 \
        --partition=general \
        --ntasks=1 \
        --cpus-per-task=1 \
        --mem=4G \
        --account=r01704 \
        "$0" "$@"
    exit $?
fi

exec > ${PROJECT_BASE_DIR}/workflow/master_debug.log 2>&1
set -x

module load conda/25.3.0
source activate icmh-dlc-310

cd ${PROJECT_BASE_DIR}/workflow
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