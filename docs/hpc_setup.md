# HPC Setup

## Conda Environment
We have env files for both Linux and Windows. If you're running this on the cluster:

```bash
module load mamba/latest
mamba env create -f envs/environment_linux.yml
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
Once videos are in `staging/`:

```bash
sbatch /N/project/msk_dl/icmh-dlc-final-scripts/scripts/submit_workflow.sh
```
