import os
import shutil
from moviepy.video.io.VideoFileClip import VideoFileClip

# Snakemake injects this object at runtime. The mock below allows the
# script to be linted and tested outside of a Snakemake context.
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
            "output_codec": "libx264",
            "frame_rate_handling_policy": "CFR",
        },
    )

ffmpeg_exe = shutil.which("ffmpeg")
if ffmpeg_exe:
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_exe

input_path = snakemake.input[0]
output_path = snakemake.output[0]

# Access config values defined in config.yaml via snakemake.config
trim_start = snakemake.config["trim_start_seconds"]
fps = snakemake.config["fps"]
duration = snakemake.config["trim_duration_seconds"]
codec = snakemake.config["output_codec"]
policy = snakemake.config["frame_rate_handling_policy"]

trim_end = trim_start + duration


def process_video():
    try:
        print(f"Processing: {input_path}")

        ffmpeg_params = []
        if policy == "CFR":
            ffmpeg_params = ["-vsync", "cfr"]

        # 1. Load the clip
        # 2. Subclip removes the "card" (start) and stops at exactly trim_end
        clip = VideoFileClip(input_path).subclipped(trim_start, trim_end)

        # Write the file
        clip.write_videofile(
            output_path,
            codec=codec,
            fps=fps,
            ffmpeg_params=ffmpeg_params,
            logger=None,  # Reduces console spam during parallel execution
        )

        clip.close()

    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        raise e


if __name__ == "__main__":
    process_video()
