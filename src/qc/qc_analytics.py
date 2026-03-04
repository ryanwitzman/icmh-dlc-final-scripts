import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import argparse


def run_qc(input_csv, output_folder, video_name):
    df = pd.read_csv(input_csv)
    os.makedirs(output_folder, exist_ok=True)

    target_x = "mouse_center_x"
    target_y = "mouse_center_y"

    # 1. Keypoint Confidence Summary
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

    # 2. Trajectory Plot
    plt.figure(figsize=(8, 6))
    plt.plot(df[target_x], df[target_y], color="blue", alpha=0.5, lw=1)
    plt.title(f"Trajectory: {video_name}")
    plt.xlabel("X (arena coords)")
    plt.ylabel("Y (arena coords)")
    plt.gca().invert_yaxis()
    plt.savefig(os.path.join(output_folder, f"{video_name}_trajectory.png"))
    plt.close()

    # 3. Heatmap Occupancy
    plt.figure(figsize=(8, 6))
    plt.hist2d(df[target_x].dropna(), df[target_y].dropna(), bins=50, cmap="hot")
    plt.colorbar(label="Frame Count")
    plt.title(f"Heatmap: {video_name}")
    plt.savefig(os.path.join(output_folder, f"{video_name}_heatmap.png"))
    plt.close()

    # 4. Speed Over Time
    df["dx"] = df[target_x].diff()
    df["dy"] = df[target_y].diff()
    df["speed"] = np.sqrt(df["dx"] ** 2 + df["dy"] ** 2)

    plt.figure(figsize=(10, 4))
    plt.plot(df["speed"], color="green")
    plt.title(f"Speed over Time: {video_name}")
    plt.ylabel("Speed (pixels/frame)")
    plt.savefig(os.path.join(output_folder, f"{video_name}_speed.png"))
    plt.close()

    return stats


def needs_header(path):
    """Return True if the file doesn't exist or is empty/header-only."""
    if not os.path.exists(path):
        return True
    return os.path.getsize(path) == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--vid", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    qc_stats = run_qc(args.input, args.outdir, args.vid)

    summary_df = pd.DataFrame([qc_stats])
    write_header = needs_header(args.summary)
    summary_df.to_csv(args.summary, mode="a", index=False, header=write_header)
    print(f"[QC] Appended stats for '{args.vid}' → {args.summary}")
