# HPC Setup

## Conda Environment
We have env files for both Linux and Windows. If you're running this on the cluster:

```bash
module load conda/25.3.0
conda env create -f envs/environment.yml
conda activate icmh-dlc-310
```
This installs DeepLabCut 2.3.11 and all the dependencies.

## SharePoint Credentials
If you're using the ingest rule to pull videos from SharePoint, you need an `.env` file in the root directory. 

```
TENANT_ID=your_id
CLIENT_ID=your_client
CLIENT_SECRET=your_secret
```
The ingest rule is commented out in the Snakefile by default. If you're manually placing videos in `staging/`, you can ignore this.

## Slurm Setup
Slurm jobs are managed through Snakemake using `workflow/cluster.yaml`. 

- CPU jobs (resize, postprocess, qc) run on the `general` partition. Account is set to `r01704`.
- GPU jobs (`trim_video`,`dlc_inference`) run on the `gpu` partition. It requests 1 GPU and 16GB RAM for 1 hour.

If a job times out or runs out of memory, change the values in `workflow/cluster.yaml`.

## Running
Once videos are in `staging/` and you are in the main project directory:

If you just want to run the trimmer by itself without the whole pipeline:
```bash
sbatch scripts/submit_trim_job.sh
```

If you just want to run DeepLabCut inference directly on your resized videos:
```bash
sbatch scripts/submit_dlc_inference.sh
```

To run the full end-to-end Snakemake workflow:
```bash
sbatch scripts/submit_workflow.sh
```

## Retrieving Logs
There are two main places where logs are generated:

### 1. Slurm Job Logs (Master Scripts)
Whenever you submit a job using `sbatch` (like the trimmer job, DLC inference job, or the master Snakemake job), Slurm generates files holding the standard output and standard errors.

These scripts are designed to dynamically read the `base_dir` variable you set in `configs/config.yaml`. The logs are **always**  saved in the path: `<base_dir>/logs/`. 

To check if the master job crashed or see its progress, you can read the `.out` or `.err` files:
```bash
cat logs/trim_videos_*.out
cat logs/dlc_inference_*.err
cat logs/snakemake_master_*.out
cat logs/slurm_*.out
```

### 2. Snakemake Pipeline Logs (Individual Rules)
If you run the full Snakemake workflow, every individual step (resize, inference, qc, etc.) generates its own dedicated log file so you can debug exactly which video failed. These are saved in `outputs/logs/{batch_id}` and are named by the the rule.

For example, to check the inference log for a specific batch:
```bash
cat outputs/logs/{batch_id}/{vid}_inference.log
```
