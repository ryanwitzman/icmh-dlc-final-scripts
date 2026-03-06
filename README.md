# icmh-dlc-final-scripts

Final Snakemake pipeline for running DeepLabCut (DLC) inference on top view mouse behavior videos. 

This handles everything from pulling raw videos from SharePoint to the final post-processed CSVs. 

Docs:
- `docs/pipeline_overview.md`: What each step of the pipeline does.
- `docs/hpc_setup.md`: Getting the conda env and Slurm set up.
- `docs/troubleshooting.md`: Common errors and how to fix them.

## Quick Start

1. Clone this to your scratch or project dir on the cluster.
2. Build the env:
   ```bash
   mamba env create -f envs/environment_linux.yml
   conda activate icmh-dlc-310
   ```
3. Put your raw `.mp4` videos in `staging/` (if not using the ingest script).
4. Run it:
   ```bash
   sbatch /N/project/msk_dl/icmh-dlc-final-scripts/scripts/submit_workflow.sh
   ```

Note: The resize rule needs FFmpeg 6.1 to work right.
