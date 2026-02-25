import argparse
import os
import time
import logging
import shutil
import glob
import sys
import deeplabcut

# Add conda env's CUDA runtime to DLL search path (Windows only)
# This is necessary because Windows doesn't auto-search conda's Library/bin
conda_env = os.path.dirname(sys.executable)  # e.g. .../envs/icmh-dlc
cuda_dll_path = os.path.join(conda_env, "Library", "bin")
if os.path.exists(cuda_dll_path):
    os.add_dll_directory(cuda_dll_path)


def setup_logger(log_file):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger()


def main():
    parser = argparse.ArgumentParser(
        description="Run DLC SuperAnimal Inference on a list of trimmed videos."
    )
    parser.add_argument(
        "--videos",
        required=True,
        nargs="+",
        help="List of paths to the trimmed videos.",
    )

    # Removed --dlc_config since SuperAnimal handles weights automatically
    parser.add_argument(
        "--out_dir", required=True, help="Directory to save DLC output (H5/CSV)."
    )
    parser.add_argument(
        "--log_file", required=True, help="Path to save the execution log."
    )
    args = parser.parse_args()

    logger = setup_logger(args.log_file)
    logger.info(f"Starting DLC SuperAnimal Inference for videos: {args.videos}")

    # Check GPU Allocation
    cuda_devices = os.environ.get("CUDA_VISIBLE_DEVICES", "Not Set / CPU")
    logger.info(f"GPU Allocation (CUDA_VISIBLE_DEVICES): {cuda_devices}")

    os.makedirs(args.out_dir, exist_ok=True)
    start_time = time.time()

    try:
        # Run inference using the pre-trained SuperAnimal Model Zoo
        deeplabcut.video_inference_superanimal(
            args.videos,
            "superanimal_topviewmouse",
            videotype=".mp4",
            video_adapt=False,  # Set to True if you want to perform unsupervised video adaptation
        )

        # SuperAnimal typically saves output files in the same directory as the input video.
        for video_path in args.videos:
            video_dir = os.path.dirname(os.path.abspath(video_path))
            base_name = os.path.splitext(os.path.basename(video_path))[0]

            # Find all files generated for this video (h5, csv, pickle)
            generated_files = glob.glob(
                os.path.join(video_dir, f"{base_name}*superanimal*")
            )
            for file_path in generated_files:
                shutil.move(
                    file_path, os.path.join(args.out_dir, os.path.basename(file_path))
                )

        runtime = time.time() - start_time
        logger.info(f"SUCCESS: Inference completed in {runtime:.2f} seconds.")

    except Exception as e:
        logger.error(f"FAILED: Inference error occurred: {e}", exc_info=True)
        raise e


if __name__ == "__main__":
    main()
