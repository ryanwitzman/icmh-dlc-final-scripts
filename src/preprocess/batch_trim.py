import subprocess
import time
import yaml
from pathlib import Path
from datetime import datetime

config_path = Path(__file__).resolve().parent.parent.parent / "configs" / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

input_dir = Path(config.get("base_dir", ".")) / config.get(
    "staging_dir", "staging"
).strip("../")
output_dir_base = Path(config.get("base_dir", ".")) / config.get(
    "output_dir_path", "outputs"
).strip("../")

batch_id = config.get("batch_id", "auto")
if batch_id == "auto":
    batch_id = datetime.now().strftime("batch_%Y%m%d_%H%M%S")

batch_dir = output_dir_base / batch_id
output_dir = batch_dir / "trimmed"
ext = config.get("output_container", "mp4").strip(".")
log_file = batch_dir / "logs" / "batch_trim_log.txt"

output_dir.mkdir(parents=True, exist_ok=True)
(batch_dir / "logs").mkdir(parents=True, exist_ok=True)

with open(log_file, "a") as log:
    log.write(f"\n--- Batch Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    videos = list(input_dir.rglob("*.mp4")) + list(input_dir.rglob("*.MP4"))
    for video in videos:
        print(f"Processing {video.name}...")
        t0 = time.time()
        trim_script = str(Path(__file__).resolve().parent / "trim_video.py")
        result = subprocess.run(
            ["python", trim_script, "--input-file", str(video)],
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
