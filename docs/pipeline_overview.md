# Pipeline Overview

## 1. Ingest (Optional)
Rule: `ingest.smk`
Pulls raw `.mp4` videos from the Kacena Lab SharePoint into `staging/`. It's disabled in the `Snakefile` by default, assuming you just put the videos in `staging/` manually.

## 2. Preprocess
Rule: `preprocess.smk`
Trims the first 60 seconds off so we skip the setup time, and keeps 15 seconds of footage for testing (change `trim_duration_seconds` to 300 in `configs/config.yaml` for actual runs). This runs on the `gpu` partition.

## 3. Resize
Rule: `resize.smk`
Scales the video down by half (`iw/2:ih/2`), encodes with `libx264`, and forces a constant frame rate of 30fps so audio/video sync doesn't break. You need FFmpeg 7.0.2 for this.

## 4. DLC Inference
Rule: `dlc_inference.smk`
Runs DeepLabCut 2.3.5 using the `superanimal_topviewmouse` model. This runs on the `gpu` partition.

## 5. Postprocess
Rule: `postprocess.smk`
Cleans up the raw DLC output. Any points with a likelihood below 0.6 get replaced with `NaN` so they don't mess up downstream analysis.

## 6. QC
Rule: `qc.smk`
Aggregates the post-processed CSVs into a single `qc_summary.csv` in `outputs/`. Creates a heatmap, speed graph, and a tr This is the final target rule in the pipeline.
