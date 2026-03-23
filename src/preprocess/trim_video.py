import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime

import yaml

from pathlib import Path

trim_start = 60
fps = 30
duration = 300
policy = "CFR"
use_gpu = True
input_path = ""
output_path = ""
codec = "libx264"
ext = "mp4"


def parse_and_setup():
    global trim_start, fps, duration, policy, use_gpu, input_path, output_path, codec, ext
    try:
        snakemake
    except NameError:
        parser = argparse.ArgumentParser(
            description="Trim one video using optimized ffmpeg."
        )
        parser.add_argument("--input-file", required=True, help="Path to raw MP4 file")
        parser.add_argument(
            "--output-file", required=False, help="Dest path (optional)"
        )
        args = parser.parse_args()

        config_path = Path(__file__).parent.parent.parent / "configs" / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        input_path = str(Path(args.input_file))

        trim_start = config["trim_start_seconds"]
        fps = config["fps"]
        duration = config["trim_duration_seconds"]
        policy = config["frame_rate_handling_policy"]
        use_gpu = config.get("use_gpu", True)
        codec = config.get("output_codec", "libx264")
        ext = config.get("output_container", "mp4")

        if args.output_file:
            output_path = str(Path(args.output_file))
        else:
            out_dir_base = Path(config.get("output_dir_path", "outputs"))
            batch_id = config.get("batch_id", "auto")
            if batch_id == "auto":
                batch_id = datetime.now().strftime("batch_%Y%m%d_%H%M%S")
            out_dir = out_dir_base / "trimmed" / batch_id
            fname = f"trimmed_{Path(input_path).stem}.{ext.strip('.')}"
            output_path = str(out_dir / fname)
    else:
        input_path = snakemake.input[0]
        output_path = snakemake.output[0]
        trim_start = snakemake.config["trim_start_seconds"]
        fps = snakemake.config["fps"]
        duration = snakemake.config["trim_duration_seconds"]
        policy = snakemake.config["frame_rate_handling_policy"]
        use_gpu = snakemake.config.get("use_gpu", True)
        codec = snakemake.config.get("output_codec", "libx264")
        ext = snakemake.config.get("output_container", "mp4")


ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"


def has_nvenc() -> bool:
    try:
        result = subprocess.run(
            [ffmpeg_exe, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return "h264_nvenc" in result.stdout
    except FileNotFoundError:
        return False


def build_ffmpeg_cmd(input_path: str, output_path: str, gpu: bool) -> list[str]:
    start_str = str(trim_start)
    duration_str = str(duration)

    if gpu:
        video_input_args = ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
        video_encode_args = [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p4",
            "-rc",
            "vbr",
            "-cq",
            "23",
        ]
    else:
        video_input_args = []
        video_encode_args = ["-c:v", codec, "-crf", "23", "-preset", "fast"]

    vsync_args = ["-vsync", "cfr"] if policy == "CFR" else []

    cmd = (
        [ffmpeg_exe, "-y"]
        + video_input_args
        + [
            "-ss",
            start_str,
            "-i",
            input_path,
            "-t",
            duration_str,
        ]
        + video_encode_args
        + ["-r", str(fps)]
        + vsync_args
        + ["-c:a", "aac"]
        + [output_path]
    )
    return cmd


def process_video():
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    gpu = use_gpu and has_nvenc()
    if use_gpu and not gpu:
        print(
            "WARNING: use_gpu=true but NVENC not found — falling back to CPU (libx264)."
        )

    cmd = build_ffmpeg_cmd(input_path, output_path, gpu=gpu)
    encoder = "h264_nvenc (GPU)" if gpu else "libx264 (CPU)"
    print(f"Processing: {input_path}  ->  {output_path}  [{encoder}]")
    print(f"FFmpeg cmd: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            print(result.stderr)
            raise RuntimeError(f"FFmpeg failed with code {result.returncode}")
        print(f"Done: {output_path}")

        provenance = {
            "source_video": input_path,
            "output_video": output_path,
            "trim_start_seconds": trim_start,
            "trim_duration_seconds": duration,
            "fps": fps,
            "output_codec": codec,
            "output_container": ext,
            "frame_rate_policy": policy,
            "gpu_used": gpu,
            "encoder": encoder,
            "timestamp": datetime.now().isoformat(),
        }
        prov_path = output_path.rsplit(".", 1)[0] + "_provenance.json"
        with open(prov_path, "w") as pf:
            json.dump(provenance, pf, indent=2)
        print(f"Provenance card: {prov_path}")

    except FileNotFoundError:
        print(
            f"Error: FFmpeg executable not found at "
            f"'{ffmpeg_exe}'. Please ensure it is "
            f"installed and in your PATH."
        )
        import sys

        sys.exit(1)


if __name__ == "__main__":
    parse_and_setup()
    process_video()
