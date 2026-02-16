######## snakemake preamble start (automatically inserted, do not edit) ########
import sys;sys.path.extend(['/Users/ryanwitzman/icmh-scripts/venv/lib/python3.12/site-packages', '/Users/ryanwitzman/icmh-scripts/workflow', '/Users/ryanwitzman/icmh-scripts/venv/bin', '/opt/homebrew/Cellar/python@3.12/3.12.4/Frameworks/Python.framework/Versions/3.12/lib/python3.12', '/opt/homebrew/Cellar/python@3.12/3.12.4/Frameworks/Python.framework/Versions/3.12/lib/python3.12/lib-dynload', '/Users/ryanwitzman/icmh-scripts/venv/lib/python3.12/site-packages', '/Users/ryanwitzman/Library/Caches/snakemake/snakemake/source-cache/snakemake-runtime-cache/tmpa3a_o77m/file/Users/ryanwitzman/icmh-scripts/workflow/../src/trim', '/Users/ryanwitzman/icmh-scripts/workflow/../src/trim']);import pickle;from snakemake import script;script.snakemake = pickle.loads(b'\x80\x04\x95R\x04\x00\x00\x00\x00\x00\x00\x8c\x10snakemake.script\x94\x8c\tSnakemake\x94\x93\x94)\x81\x94}\x94(\x8c\x05input\x94\x8c\x0csnakemake.io\x94\x8c\nInputFiles\x94\x93\x94)\x81\x94\x8c)../inputs/nputs/AAL_BL_3-25-24_OF_RM1.MP4\x94a}\x94(\x8c\x06_names\x94}\x94\x8c\x12_allowed_overrides\x94]\x94(\x8c\x05index\x94\x8c\x04sort\x94eh\x10h\x06\x8c\x0eAttributeGuard\x94\x93\x94)\x81\x94}\x94\x8c\x04name\x94h\x10sbh\x11h\x13)\x81\x94}\x94h\x16h\x11sbub\x8c\x06output\x94h\x06\x8c\x0bOutputFiles\x94\x93\x94)\x81\x94\x8c,../outputs/trimmed_AAL_BL_3-25-24_OF_RM1.MP4\x94a}\x94(h\x0c}\x94h\x0e]\x94(h\x10h\x11eh\x10h\x13)\x81\x94}\x94h\x16h\x10sbh\x11h\x13)\x81\x94}\x94h\x16h\x11sbub\x8c\r_params_store\x94h\x06\x8c\x06Params\x94\x93\x94)\x81\x94}\x94(h\x0c}\x94h\x0e]\x94(h\x10h\x11eh\x10h\x13)\x81\x94}\x94h\x16h\x10sbh\x11h\x13)\x81\x94}\x94h\x16h\x11sbub\x8c\r_params_types\x94}\x94\x8c\twildcards\x94h\x06\x8c\tWildcards\x94\x93\x94)\x81\x94\x8c\x19AAL_BL_3-25-24_OF_RM1.MP4\x94a}\x94(h\x0c}\x94\x8c\x03vid\x94K\x00N\x86\x94sh\x0e]\x94(h\x10h\x11eh\x10h\x13)\x81\x94}\x94h\x16h\x10sbh\x11h\x13)\x81\x94}\x94h\x16h\x11sb\x8c\x03vid\x94h6ub\x8c\x07threads\x94K\x01\x8c\tresources\x94h\x06\x8c\x0cResourceList\x94\x93\x94)\x81\x94(\x8c0/var/folders/y_/39v4gzrs6msd4px_2n26rv580000gn/T\x94K\x01K\x01e}\x94(h\x0c}\x94(\x8c\x06tmpdir\x94K\x00N\x86\x94\x8c\x06_nodes\x94K\x01N\x86\x94\x8c\x06_cores\x94K\x02N\x86\x94uh\x0e]\x94(h\x10h\x11eh\x10h\x13)\x81\x94}\x94h\x16h\x10sbh\x11h\x13)\x81\x94}\x94h\x16h\x11sbhIhFhKK\x01hMK\x01ub\x8c\x03log\x94h\x06\x8c\x03Log\x94\x93\x94)\x81\x94}\x94(h\x0c}\x94h\x0e]\x94(h\x10h\x11eh\x10h\x13)\x81\x94}\x94h\x16h\x10sbh\x11h\x13)\x81\x94}\x94h\x16h\x11sbub\x8c\x06config\x94}\x94(\x8c\x12trim_start_seconds\x94K\x1e\x8c\x03fps\x94K\x1e\x8c\x15trim_duration_seconds\x94M,\x01\x8c\x0coutput_codec\x94\x8c\x07libx264\x94\x8c\x1aframe_rate_handling_policy\x94\x8c\x03CFR\x94u\x8c\x04rule\x94\x8c\ntrim_video\x94\x8c\x0fbench_iteration\x94N\x8c\tscriptdir\x94\x8c4/Users/ryanwitzman/icmh-scripts/workflow/../src/trim\x94ub.');del script;from snakemake.logging import logger;from snakemake.script import snakemake;__real_file__ = __file__; __file__ = '/Users/ryanwitzman/icmh-scripts/src/trim/trim_video.py';
######## snakemake preamble end #########
import os
import shutil
from moviepy.video.io.VideoFileClip import VideoFileClip

import imageio_ffmpeg as ffmpeg
ffmpeg_exe = shutil.which("ffmpeg")
if ffmpeg_exe:
    os.environ['IMAGEIO_FFMPEG_EXE'] = ffmpeg_exe

input_path = snakemake.input[0]
output_path = snakemake.output[0]

# Access config values defined in config.yaml via snakemake.config
trim_start = snakemake.config['trim_start_seconds']
fps = snakemake.config['fps']
duration = snakemake.config['trim_duration_seconds']
codec = snakemake.config['output_codec']
policy = snakemake.config['frame_rate_handling_policy']

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
            logger=None # Reduces console spam during parallel execution
        )
        
        clip.close() 
        
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        raise e

if __name__ == "__main__":
    process_video()