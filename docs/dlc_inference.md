# DeepLabCut Inference on HPC

## Inputs
- **Trimmed Videos:** These come out of the `preprocess` and `resize` steps (usually sitting in `outputs/trimmed_resized/`).
- **DLC Project/Config:** You can point the inference script to `configs/config.yaml` (which contains your model weights and settings), or you can just use the built-in SuperAnimal models (e.g., `superanimal_topviewmouse`).

## Outputs
- **DLC Output Files:** The script spits out tracking data, most importantly the `.h5` files, which get saved to `outputs/dlc_results/`. The postprocess step will later clean this up into a nice CSV file.
- **Logs:** A detailed log file correctly captures everything—from the overall runtime, to GPU allocation (scraped from `nvidia-smi`), to any low-level errors DLC throws. You'll find these organized natively per video in `outputs/logs/{vid}_inference.log`.


## Documentation
### Environment & Installation
DeepLabCut 2.3.11 is installed via Mamba/Conda. If you need to recreate it:
```bash
module load mamba/latest
mamba env create -f envs/environment_linux.yml
conda activate icmh-dlc-310
```

### DLC Project Path Conventions
If you're swapping out SuperAnimal for a custom trained model, you'll need to change that in `configs/config.yaml`.

Because DLC normally writes outputs directly into whatever directory the video lives in, our wrapper script  grabs all the newly-made `.h5`, `.csv`, and `.pickle` files and relocates them to `outputs/dlc_results/`.

### Output Logs
The logging is cleanly organized per batch/video. If you have `outputs/trimmed_resized/trimmed_video1.mp4`, its corresponding runtime log will be waiting at `outputs/logs/video1_inference.log`. If inference fails or takes forever, checking that file will tell you if Snakemake couldn't find a GPU or if DLC messed up on something internally.
