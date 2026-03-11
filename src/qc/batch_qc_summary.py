import pandas as pd
from pathlib import Path
import yaml

with open("configs/config.yaml") as f:
    config = yaml.safe_load(f)

output_dir = Path(config.get("base_dir", ".")) / config.get(
    "output_dir_path", "outputs"
).strip("../")
qc_dir = output_dir / "qc"
summary_file = output_dir / "qc_summary.csv"

stats_files = list(qc_dir.rglob("*_stats.csv"))
df_list = [pd.read_csv(f) for f in stats_files]

if df_list:
    pd.concat(df_list, ignore_index=True).to_csv(summary_file, index=False)
    print(f"Aggregated {len(stats_files)} QC files into {summary_file}")
else:
    with open(summary_file, "w") as f:
        f.write("video,mean_conf,median_conf,frac_below_thresh\n")
    print(f"No QC stats found. Created empty {summary_file}")
