import subprocess
import time
import yaml
from pathlib import Path
from datetime import datetime

with open("configs/config.yaml") as f:
    config = yaml.safe_load(f)

input_dir = Path(config.get("base_dir", ".")) / config.get("input_dir", "inputs").strip(
    "../"
)
output_dir = Path(config.get("base_dir", ".")) / config.get(
    "output_dir_path", "outputs"
).strip("../")
ext = config.get("output_container", "mp4").strip(".")
log_file = output_dir / "logs" / "batch_trim_log.txt"

output_dir.mkdir(parents=True, exist_ok=True)
(output_dir / "logs").mkdir(parents=True, exist_ok=True)

with open(log_file, "a") as log:
    log.write(f"\n--- Batch Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    for video in input_dir.rglob("*.mp4"):
        print(f"Processing {video.name}...")
        t0 = time.time()
        result = subprocess.run(
            ["python", "src/preprocess/trim_video.py", "--input-file", str(video)],
            capture_output=True,
            text=True,
        )
        elapsed = time.time() - t0

        out_file = output_dir / f"trimmed_{video.stem}.{ext}"
        if result.returncode == 0 and out_file.exists():
            size_mb = out_file.stat().st_size / 1e6
            status = f"SUCCESS | output={out_file} | size={size_mb:.1f}MB | time={elapsed:.1f}s"
        elif result.returncode == 0:
            status = f"SUCCESS | output not found at {out_file} | time={elapsed:.1f}s"
        else:
            status = f"FAILED | time={elapsed:.1f}s | {result.stderr.strip()}"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        src_size_mb = video.stat().st_size / 1e6
        log.write(f"[{timestamp}] {video.name} (src={src_size_mb:.1f}MB): {status}\n")
        print(f"{video.name}: {status}")
