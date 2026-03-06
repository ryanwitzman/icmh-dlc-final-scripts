# Pipeline Overview

## 1. Ingest (Optional)
Rule: `ingest.smk`
Pulls raw `.mp4` videos from the Kacena Lab SharePoint into `staging/`. It's disabled in the `Snakefile` by default, assuming you just put the videos in `staging/` manually.

**Expected Inputs:** SharePoint URL and remote path (credentials from config/env)
**Expected Outputs:** `staging/_logs/{batch_id}_manifest.csv`, `staging/_logs/{batch_id}.ingest.done`
**Logs:** `staging/_logs/{batch_id}_ingest_snakemake.log`

## 2. Preprocess
Rule: `preprocess.smk`
Trims the first 60 seconds off so we skip the setup time, and keeps 15 seconds of footage for testing (change `trim_duration_seconds` to 300 in `configs/config.yaml` for actual runs). This runs on the `gpu` partition.

**Expected Inputs:** Raw video `staging/{vid}.mp4`
**Expected Outputs:** `outputs/trimmed_{vid}.mp4`
**Logs:** `outputs/logs/{vid}_preprocess.log`

## 3. Resize
Rule: `resize.smk`
Scales the video down by half (`iw/2:ih/2`), encodes with `libx264`, and forces a constant frame rate of 30fps so audio/video sync doesn't break. You need FFmpeg 6.1 for this.

**Expected Inputs:** Trimmed video `outputs/trimmed_{vid}.mp4`
**Expected Outputs:** Downscaled video `outputs/trimmed_resized/trimmed_{vid}.mp4`
**Logs:** `outputs/logs/{vid}_resize.log`

## 4. DLC Inference
Rule: `dlc_inference.smk`
Runs DeepLabCut 2.3.5 using the `superanimal_topviewmouse` model. This runs on the `gpu` partition.

**Expected Inputs:** Resized video `outputs/trimmed_resized/trimmed_{vid}.mp4`
**Expected Outputs:** `outputs/dlc_results/{vid}_superanimal.h5`
**Logs:** `outputs/logs/{vid}_inference.log`

## 5. Postprocess
Rule: `postprocess.smk`
Cleans up the raw DLC output. Any points with a likelihood below 0.6 get replaced with `NaN` so they don't mess up downstream analysis.

**Expected Inputs:** H5 inference output `outputs/dlc_results/{vid}_superanimal.h5`
**Expected Outputs:** `outputs/postprocessed/{vid}.csv`
**Logs:** `outputs/logs/{vid}_postprocess.log`

## 6. QC
Rule: `qc.smk`
Aggregates the post-processed CSVs into a single `qc_summary.csv` in `outputs/`. Creates a heatmap, speed graph, and a tr This is the final target rule in the pipeline.

**Expected Inputs:** Postprocessed CSV `outputs/postprocessed/{vid}.csv`
**Expected Outputs:** 
- `outputs/qc/{vid}/{vid}_trajectory.png`
- `outputs/qc/{vid}/{vid}_heatmap.png`
- `outputs/qc/{vid}/{vid}_speed.png`
- `outputs/qc/{vid}/{vid}_stats.csv`
- Global summary `outputs/qc_summary.csv`
**Logs:** `outputs/logs/{vid}_qc.log`
