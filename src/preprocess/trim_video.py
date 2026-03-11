import os
import shutil
import subprocess

try:
    snakemake
except NameError:
    from types import SimpleNamespace

    snakemake = SimpleNamespace(
        input=["inputs/test_video.mp4"],
        output=["outputs/trimmed_test_video.mp4"],
        config={
            "trim_start_seconds": 60,
            "fps": 30,
            "trim_duration_seconds": 300,
            "output_codec": "libx264",  # fallback if no GPU
            "frame_rate_handling_policy": "CFR",
            "use_gpu": True,
        },
    )


input_path = snakemake.input[0]
output_path = snakemake.output[0]
trim_start = snakemake.config["trim_start_seconds"]
fps = snakemake.config["fps"]
duration = snakemake.config["trim_duration_seconds"]
policy = snakemake.config["frame_rate_handling_policy"]
use_gpu = snakemake.config.get("use_gpu", True)

ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"


def has_nvenc() -> bool:
    """Return True if this machine has a working NVENC encoder."""
    try:
        result = subprocess.run(
            [ffmpeg_exe, "-hide_banner", "-encoders"], capture_output=True, text=True
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
        video_encode_args = ["-c:v", "libx264", "-crf", "23", "-preset", "fast"]

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
    print(f"Processing: {input_path}  →  {output_path}  [{encoder}]")
    print("FFmpeg cmd:", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"FFmpeg failed with code {result.returncode}")

    print(f"Done: {output_path}")


if __name__ == "__main__":
    process_video()
