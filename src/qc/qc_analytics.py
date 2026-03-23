import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import argparse


def run_qc(input_csv, output_folder, video_name, stats_out):
    df = pd.read_csv(input_csv)
    os.makedirs(output_folder, exist_ok=True)

    target_x = "mouse_center_x"
    target_y = "mouse_center_y"

    likelihood_cols = [
        c for c in df.columns if "likelihood" in c.lower() or "prob" in c.lower()
    ]

    if likelihood_cols:
        conf_data = df[likelihood_cols].values.flatten()
        threshold = 0.6

        mean_conf = np.nanmean(conf_data)
        median_conf = np.nanmedian(conf_data)

        filled_conf = np.nan_to_num(conf_data, nan=0.0)
        frac_below_thresh = np.mean(filled_conf < threshold)
    else:
        mean_conf, median_conf, frac_below_thresh = np.nan, np.nan, np.nan

    stats = {
        "video": video_name,
        "mean_conf": mean_conf,
        "median_conf": median_conf,
        "frac_below_thresh": frac_below_thresh,
    }

    if target_x in df.columns and target_y in df.columns:
        plt.figure(figsize=(8, 6))
        plt.plot(df[target_x], df[target_y], color="blue", alpha=0.5, lw=1)
        plt.title(f"Trajectory: {video_name}")
        plt.xlabel("X (arena coords)")
        plt.ylabel("Y (arena coords)")
        plt.gca().invert_yaxis()
        plt.savefig(os.path.join(output_folder, f"{video_name}_trajectory.png"))
        plt.close()

        plt.figure(figsize=(8, 6))

        valid_data = df.dropna(subset=[target_x, target_y])
        if not valid_data.empty:
            plt.hist2d(valid_data[target_x], valid_data[target_y], bins=50, cmap="hot")
            plt.colorbar(label="Frame Count")
        plt.title(f"Heatmap: {video_name}")
        plt.gca().invert_yaxis()
        plt.savefig(os.path.join(output_folder, f"{video_name}_heatmap.png"))
        plt.close()

        df["dx"] = df[target_x].diff()
        df["dy"] = df[target_y].diff()
        df["speed"] = np.sqrt(df["dx"] ** 2 + df["dy"] ** 2)

        plt.figure(figsize=(10, 4))
        plt.plot(df["speed"], color="green")
        plt.title(f"Speed over Time: {video_name}")
        plt.ylabel("Speed (pixels/frame)")
        plt.xlabel("Frame")
        plt.savefig(os.path.join(output_folder, f"{video_name}_speed.png"))
        plt.close()

    summary_df = pd.DataFrame([stats])
    summary_df.to_csv(stats_out, index=False)
    print(f"[QC] Wrote stats for '{video_name}' → {stats_out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--vid", required=True)
    parser.add_argument("--stats_out", required=True)
    args = parser.parse_args()

    run_qc(args.input, args.outdir, args.vid, args.stats_out)
