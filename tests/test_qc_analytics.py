import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qc import qc_analytics

def test_qc_analytics_logic(tmp_path):
    output_dir = tmp_path / "qc"
    stats_out = tmp_path / "stats.csv"
    vid_name = "testvideo"

    csv_path = tmp_path / "input.csv"
    data = {
        "frame": [0, 1, 2],
        "mouse_center_x": [10.0, 15.0, 20.0],
        "mouse_center_y": [10.0, 15.0, 20.0],
        "mouse_center_likelihood": [0.99, 0.99, 0.4],
    }

    pd.DataFrame(data).to_csv(csv_path, index=False)

    qc_analytics.run_qc(csv_path, output_dir, vid_name, stats_out)

    assert (output_dir / "testvideo_trajectory.png").exists()
    assert (output_dir / "testvideo_heatmap.png").exists()
    assert (output_dir / "testvideo_speed.png").exists()

    stats_df = pd.read_csv(stats_out)
    assert stats_df.iloc[0]["video"] == "testvideo"
    assert "mean_conf" in stats_df.columns
    assert abs(stats_df.iloc[0]["frac_below_thresh"] - 0.333) < 0.01
