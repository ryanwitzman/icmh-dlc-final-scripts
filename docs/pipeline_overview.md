# Pipeline Overview
## NOTE
You may have to change the requirements in the file `workflow/cluster.yaml` depending on how many videos you have to process. The current settings are good for processing one 5 minute (9000 frames) video of the top view of a mouse.

## Batch Organization
All outputs are organized under `outputs/{rule}/{batch_id}/`. By default, `batch_id` is set to `auto` in `configs/config.yaml`, which generates a timestamp-based ID (e.g. `batch_20260312_160000`) each time you run the pipeline. Set it to a fixed name like `batch_001` to pin a specific batch.

## 1. Preprocess
Rule: `preprocess.smk`
Trims the first 60 seconds off so we skip the setup time, and keeps 300 seconds of footage for testing.

If you want to run this outside of Snakemake, you can just run `python3 src/preprocess/batch_trim.py` to loop through all the `.mp4` files in the input folder and trim them all at once. It drops a quick run log in `outputs/batch_trim_log.txt` so you can see if anything failed.

**Expected Inputs:** Raw video `staging/{vid}.mp4` (or `inputs/` for the batch script)
**Expected Outputs:** `outputs/trimmed/{batch_id}/trimmed_{vid}.mp4`
**Logs:** `outputs/logs/{batch_id}/{vid}_preprocess.log` (and `outputs/logs/{batch_id}/batch_trim_log.txt`)

## 2. Resize
Rule: `resize.smk`
Scales the video down by half (`iw/2:ih/2`), encodes with `libx264`, and forces a constant frame rate of 30fps so audio/video sync doesn't break. You need FFmpeg 6.1 for this.

**Expected Inputs:** Trimmed video `outputs/trimmed/{batch_id}/trimmed_{vid}.mp4`
**Expected Outputs:** Downscaled video `outputs/resized/{batch_id}/trimmed_{vid}.mp4`
**Logs:** `outputs/logs/{batch_id}/{vid}_resize.log`

## 3. DLC Inference
Rule: `dlc_inference.smk`
Runs DeepLabCut 2.3.11 using the `superanimal_topviewmouse` model. This runs on the `gpu-interactive` partition. You may need to switch to `gpu` partition if inference is expected to take longer than 4 hours.

If you don't want to use Snakemake, you can submit the standalone job:
```bash
bash scripts/submit_dlc_inference.sh
```
This automatically crawls your `outputs/resized` folder and runs inference on every video it finds, dropping the results into `outputs/dlc_results/{batch_id}/`.

**Expected Inputs:** Resized video `outputs/resized/{batch_id}/trimmed_{vid}.mp4`
**Expected Outputs:** `outputs/dlc_results/{batch_id}/{vid}_superanimal.h5`
**Logs:** `outputs/logs/{batch_id}/{vid}_inference.log` (and Snakemake logs or `dlc_inference_*.out` for the standalone run)

## 4. Postprocess
Rule: `postprocess.smk`
Cleans up the raw DLC output. Any points with a likelihood below 0.6 get replaced with `NaN` so they don't mess up analysis.

**Expected Inputs:** H5 inference output `outputs/dlc_results/{batch_id}/{vid}_superanimal.h5`
**Expected Outputs:** `outputs/postprocessed/{batch_id}/{vid}.csv`
**Logs:** `outputs/logs/{batch_id}/{vid}_postprocess.log`

## 5. QC
Rule: `qc.smk`
Aggregates the post-processed CSVs into a single `qc_summary.csv`. Creates a heatmap, speed graph, and a trajectory plot.

**Expected Inputs:** Postprocessed CSV `outputs/postprocessed/{batch_id}/{vid}.csv`
**Expected Outputs:** 
- `outputs/qc/{batch_id}/{vid}/{vid}_trajectory.png`
- `outputs/qc/{batch_id}/{vid}/{vid}_heatmap.png`
- `outputs/qc/{batch_id}/{vid}/{vid}_speed.png`
- `outputs/qc/{batch_id}/{vid}/{vid}_stats.csv`
- Global summary `outputs/qc/{batch_id}/qc_summary.csv`
**Logs:** `outputs/logs/{batch_id}/{vid}_qc.log`
