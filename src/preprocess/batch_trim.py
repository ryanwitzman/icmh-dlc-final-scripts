import subprocess
import time
import yaml
import glob
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

output_dir = output_dir_base / "trimmed" / batch_id
resized_dir = output_dir_base / "resized" / batch_id
ext = config.get("output_container", "mp4").strip(".")
resize_scale = config.get("resize_scale", "iw/2:ih/2")
log_file = output_dir_base / "logs" / batch_id / "batch_trim_log.txt"

log_dir = output_dir_base / "logs" / batch_id


def ensure_dir(p: Path):
    """Create directory on first use."""
    p.mkdir(parents=True, exist_ok=True)


trim_script = str(Path(__file__).resolve().parent / "trim_video.py")
resize_script = str(Path(__file__).resolve().parent / "resize_video.py")


def already_processed(subdir: str, filename: str) -> str | None:
    """Return the first matching path across all batches, or None."""
    matches = glob.glob(str(output_dir_base / subdir / "*" / filename))
    return matches[0] if matches else None


ensure_dir(log_dir)
with open(log_file, "a") as log:
    log.write(f"\n--- Batch Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    videos = sorted(input_dir.rglob("*.mp4")) + sorted(input_dir.rglob("*.MP4"))

    for video in videos:
        timestamp = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        src_size_mb = video.stat().st_size / 1e6
        trimmed_name = f"trimmed_{video.stem}.{ext}"
        resized_name = f"trimmed_{video.stem}.{ext}"

        existing_trim = already_processed("trimmed", trimmed_name)
        if existing_trim:
            trim_status = f"SKIPPED | previously trimmed at {existing_trim}"
            trimmed_out = Path(existing_trim)
        else:
            print(f"Trimming {video.name}...")
            t0 = time.time()
            ensure_dir(output_dir)
            trimmed_out = output_dir / trimmed_name
            result = subprocess.run(
                [
                    "python",
                    trim_script,
                    "--input-file",
                    str(video),
                    "--output-file",
                    str(trimmed_out),
                ],
                capture_output=True,
                text=True,
            )
            elapsed = time.time() - t0
            if result.returncode == 0 and trimmed_out.exists():
                size_mb = trimmed_out.stat().st_size / 1e6
                trim_status = f"SUCCESS | output={trimmed_out} | size={size_mb:.1f}MB | time={elapsed:.1f}s"
            elif result.returncode == 0:
                trim_status = (
                    f"SUCCESS | output not found at {trimmed_out} | time={elapsed:.1f}s"
                )
                trimmed_out = None
            else:
                trim_status = f"FAILED | time={elapsed:.1f}s | {result.stderr.strip()}"
                trimmed_out = None

        log.write(
            f"[{timestamp()}] {video.name} (src={src_size_mb:.1f}MB) [TRIM]: {trim_status}\n"
        )
        print(f"{video.name} [TRIM]: {trim_status}")

        if trimmed_out is None or not trimmed_out.exists():
            resize_status = "SKIPPED | no trimmed source available"
            log.write(
                f"[{timestamp()}] {video.name} (src={src_size_mb:.1f}MB) [RESIZE]: {resize_status}\n"
            )
            print(f"{video.name} [RESIZE]: {resize_status}")
            continue

        existing_resize = already_processed("resized", resized_name)
        if existing_resize:
            resize_status = f"SKIPPED | previously resized at {existing_resize}"
        else:
            print(f"Resizing {video.name}...")
            t0 = time.time()
            ensure_dir(resized_dir)
            resized_out = resized_dir / resized_name
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(trimmed_out),
                    "-vf",
                    f"scale={resize_scale}",
                    "-c:v",
                    "libx264",
                    "-crf",
                    "18",
                    "-preset",
                    "fast",
                    "-an",
                    str(resized_out),
                ],
                capture_output=True,
                text=True,
            )
            elapsed = time.time() - t0
            if result.returncode == 0 and resized_out.exists():
                size_mb = resized_out.stat().st_size / 1e6
                resize_status = f"SUCCESS | output={resized_out} | size={size_mb:.1f}MB | time={elapsed:.1f}s"
            elif result.returncode == 0:
                resize_status = (
                    f"SUCCESS | output not found at {resized_out} | time={elapsed:.1f}s"
                )
            else:
                resize_status = (
                    f"FAILED | time={elapsed:.1f}s | {result.stderr.strip()}"
                )

        log.write(
            f"[{timestamp()}] {video.name} (src={src_size_mb:.1f}MB) [RESIZE]: {resize_status}\n"
        )
        print(f"{video.name} [RESIZE]: {resize_status}")
