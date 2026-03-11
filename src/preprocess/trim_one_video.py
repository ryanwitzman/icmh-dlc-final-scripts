import os
import shutil
from moviepy.video.io.VideoFileClip import VideoFileClip
import imageio_ffmpeg as ffmpeg
import yaml
import argparse

parser = argparse.ArgumentParser(description="Process a video file for trimming.")
parser.add_argument(
    "--input-file",
    type=str,
    required=False,
    help="The full path to the MP4 file to be preprocessed",
)
args = parser.parse_args()

with open("configs/config.yaml") as config:
    config_vars = yaml.safe_load(config)

TRIM_START_SECONDS = config_vars["trim_start_seconds"]
FPS = config_vars["fps"]
TRIM_DURATION_SECONDS = config_vars[
    "trim_duration_seconds"
]
OUTPUT_CODEC = config_vars["output_codec"]
FRAME_RATE_HANDLING_POLICY = config_vars[
    "frame_rate_handling_policy"
]
OUTPUT_DIR_PATH = config_vars["output_dir_path"]

TRIM_END_SECONDS = TRIM_START_SECONDS + TRIM_DURATION_SECONDS

def setup_ffmpeg():
    ffmpeg_exe = shutil.which("ffmpeg")
    if ffmpeg_exe:
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_exe

    print(f"FFmpeg Version: {ffmpeg.get_ffmpeg_version()}")
    print(f"FFmpeg Path: {os.environ.get('IMAGEIO_FFMPEG_EXE', 'Not Found')}")

def process_videos():

    if args.input_file:
        video_files = [args.input_file]
    else:
        video_files = []
    output_dir_path = OUTPUT_DIR_PATH

    if not os.path.exists(output_dir_path):
        os.makedirs(output_dir_path, exist_ok=True)

    print(f"Starting processing for {len(video_files)} files...")

    ffmpeg_params = []
    if FRAME_RATE_HANDLING_POLICY == "CFR":
        ffmpeg_params = ["-vsync", "cfr"]

    for video_path in video_files:
        try:
            print(f"Processing: {video_path}")
            filename = os.path.basename(video_path)
            output_path = os.path.join(output_dir_path, f"trimmed_{filename}")

            clip = VideoFileClip(video_path).subclipped(
                TRIM_START_SECONDS, TRIM_END_SECONDS
            )

            clip.write_videofile(
                output_path, codec=OUTPUT_CODEC, fps=FPS, ffmpeg_params=ffmpeg_params
            )

            clip.close()

        except Exception as e:
            print(f"Error processing {video_path}: {e}")

if __name__ == "__main__":
    setup_ffmpeg()
    process_videos()

