import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import argparse


def run_qc(input_csv, output_folder, video_name):
    df = pd.read_csv(input_csv)
    os.makedirs(output_folder, exist_ok=True)

    # 1. Keypoint Confidence Summary
    # Assuming columns ending in '_likelihood' or '_prob' based on DLC/inference output
    likelihood_cols = [
        c for c in df.columns if "likelihood" in c.lower() or "prob" in c.lower()
    ]
    conf_data = df[likelihood_cols].values.flatten()

    threshold = 0.6
    stats = {
        "video": video_name,
        "mean_conf": np.mean(conf_data),
        "median_conf": np.median(conf_data),
        "frac_below_thresh": np.mean(conf_data < threshold),
    }

    # 2. Trajectory Plot (x-y path)
    # Assuming 'x' and 'y' for a primary bodypart like 'center' or 'snout'
    plt.figure(figsize=(8, 6))
    plt.plot(df["x"], df["y"], color="blue", alpha=0.5, lw=1)
    plt.title(f"Trajectory: {video_name}")
    plt.xlabel("X (arena coords)")
    plt.ylabel("Y (arena coords)")
    plt.gca().invert_yaxis()  # Often necessary for video coords
    plt.savefig(os.path.join(output_folder, f"{video_name}_trajectory.png"))
    plt.close()

    # 3. Heatmap Occupancy
    plt.figure(figsize=(8, 6))
    plt.hist2d(df["x"].dropna(), df["y"].dropna(), bins=50, cmap="hot")
    plt.colorbar(label="Frame Count")
    plt.title(f"Heatmap: {video_name}")
    plt.savefig(os.path.join(output_folder, f"{video_name}_heatmap.png"))
    plt.close()

    # 4. Simple Speed Over Time
    # Speed = sqrt(dx^2 + dy^2)
    df["dx"] = df["x"].diff()
    df["dy"] = df["y"].diff()
    df["speed"] = np.sqrt(df["dx"] ** 2 + df["dy"] ** 2)

    plt.figure(figsize=(10, 4))
    plt.plot(df["speed"], color="green")
    plt.title(f"Speed over Time: {video_name}")
    plt.ylabel("Speed (pixels/frame)")
    plt.savefig(os.path.join(output_folder, f"{video_name}_speed.png"))
    plt.close()

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--vid", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    qc_stats = run_qc(args.input, args.outdir, args.vid)

    # Append to summary table
    summary_df = pd.DataFrame([qc_stats])
    header = not os.path.exists(args.summary)
    summary_df.to_csv(args.summary, mode="a", index=False, header=header)
