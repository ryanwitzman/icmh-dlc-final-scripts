import argparse
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def log_environment() -> None:
    logger.info("Gathering environment and GPU allocation data...")
    try:
        import deeplabcut

        dlc_version = getattr(deeplabcut, "__version__", "unknown")
    except ImportError:
        dlc_version = "NOT INSTALLED"

    prefix = os.environ.get("CONDA_PREFIX", os.path.dirname(sys.executable))
    conda_meta = Path(prefix) / "conda-meta"

    if list(conda_meta.glob("deeplabcut-*.json")):
        install_method = f"Conda (env: {prefix})"
    else:
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pip", "show", "deeplabcut"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            install_method = (
                f"Pip (env: {prefix})"
                if r.returncode == 0
                else f"Unknown (env: {prefix})"
            )
        except Exception:
            install_method = f"Unknown (env: {prefix})"

    cuda_vis = os.environ.get("CUDA_VISIBLE_DEVICES", "NOT SET")
    gpu_lines = [f"CUDA_VISIBLE_DEVICES={cuda_vis}"]
    try:
        r = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,memory.free,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode == 0:
            for row in r.stdout.strip().splitlines():
                idx, name, mem_total, mem_free, util = [
                    c.strip() for c in row.split(",")
                ]
                gpu_lines.append(
                    f"  GPU {idx}: {name} | mem {mem_free}/{mem_total} MiB free | util {util}%"
                )
    except FileNotFoundError:
        gpu_lines.append("  nvidia-smi not found. Running on CPU?")
    except Exception as e:
        gpu_lines.append(f"  GPU query error: {e}")

    logger.info("=" * 60)
    logger.info("HARDWARE & ENVIRONMENT INFO")
    logger.info("=" * 60)
    logger.info(f"Host             : {platform.node()}")
    logger.info(f"Python           : {sys.version.split()[0]} ({sys.executable})")
    logger.info(f"DLC Version      : {dlc_version}")
    logger.info(f"DLC Install      : {install_method}")
    logger.info(f"OS               : {platform.system()} {platform.release()}")
    logger.info("GPU Allocation:\n" + "\n".join(gpu_lines))
    logger.info("=" * 60)


def collect_and_move_outputs(video_path: Path, out_dir: Path) -> None:
    stem = video_path.stem
    patterns = [f"{stem}DLC_*", f"{stem}*superanimal*", f"{stem}*.pickle"]

    found: list[Path] = []
    for pat in patterns:
        found.extend(video_path.parent.glob(pat))

    seen: set = set()
    logger.info("--- Collecting Inference Outputs ---")
    for src in found:
        if src in seen:
            continue
        seen.add(src)
        dst = out_dir / src.name
        if src.resolve() != dst.resolve():
            shutil.move(str(src), dst)
            logger.info(f"  Moved: {src.name} -> {out_dir}")
        else:
            logger.info(f"  Already in target: {dst.name}")

    if not seen:
        logger.warning("No DLC output files found beside source video!")


def main():
    parser = argparse.ArgumentParser(
        description="Run DLC inference on a trimmed video or a batch of videos.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    grp_input = parser.add_mutually_exclusive_group(required=True)
    grp_input.add_argument(
        "--videos", nargs="+", help="Path(s) to trimmed video file(s)."
    )
    grp_input.add_argument(
        "--video_dir", help="Directory containing trimmed video files."
    )

    parser.add_argument(
        "--out_dir", required=True, help="Directory to save all DLC outputs."
    )

    # Optional single-file out_h5 argument for backwards compatibility
    parser.add_argument(
        "--out_h5",
        required=False,
        help="Explicit destination for a single video's H5 output.",
    )

    grp = parser.add_mutually_exclusive_group()
    grp.add_argument(
        "--superanimal",
        default="superanimal_topviewmouse",
        metavar="MODEL_NAME",
        help="SuperAnimal model name.",
    )
    grp.add_argument(
        "--config_path", help="Path to DLC project config.yaml (standard project mode)."
    )

    parser.add_argument(
        "--video_adapt",
        action="store_true",
        help="(SuperAnimal only) Enable unsupervised video adaptation.",
    )
    args = parser.parse_args()

    log_environment()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.out_h5:
        out_h5_path = Path(args.out_h5)
        out_h5_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_h5_path = None

    if args.video_dir:
        video_dir_path = Path(args.video_dir)
        videos = list(video_dir_path.glob("*.mp4"))
        if not videos:
            logger.error(f"FATAL: No .mp4 files found in {video_dir_path}")
            sys.exit(1)
    else:
        videos = [Path(v) for v in args.videos]

    missing = [v for v in videos if not v.exists()]
    if missing:
        logger.error(f"FATAL: Video file(s) not found: {missing}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("DLC PROJECT & PATH CONVENTIONS")
    logger.info("=" * 60)
    logger.info(f"Input Videos     : {len(videos)} video(s) selected.")
    logger.info(f"Output Directory : {out_dir}")
    if out_h5_path:
        logger.info(f"Target H5 File   : {out_h5_path}")
    logger.info(f"Model/Config     : {args.config_path or args.superanimal}")
    logger.info("=" * 60)

    logger.info("Loading DeepLabCut module (this may take a moment)...")
    import deeplabcut

    logger.info("DeepLabCut successfully loaded.")

    t0 = time.time()
    try:

        if args.config_path:
            logger.info("Starting inference in Standard Project Mode...")
            deeplabcut.analyze_videos(
                args.config_path,
                [str(v) for v in videos],
                videotype=videos[0].suffix.lstrip(".") or "mp4",
                save_as_csv=True,
                destfolder=str(out_dir),
            )

        else:
            logger.info(
                f"Starting inference using SuperAnimal "
                f"({args.superanimal}) | "
                f"video_adapt={args.video_adapt}..."
            )
            deeplabcut.video_inference_superanimal(
                [str(v) for v in videos],
                args.superanimal,
                videotype=videos[0].suffix.lstrip(".") or "mp4",
                video_adapt=args.video_adapt,
            )
            for video_path in videos:
                collect_and_move_outputs(video_path, out_dir)

        logger.info("Locating target H5 files...")

        for video_path in videos:
            h5_candidates = sorted(out_dir.glob(f"{video_path.stem}*.h5"))
            if not h5_candidates:
                raise FileNotFoundError(
                    f"No H5 found in {out_dir} for "
                    f"{video_path.stem} — DLC may have "
                    f"failed silently."
                )

            src_h5 = max(h5_candidates, key=lambda p: p.stat().st_mtime)

            # Use explicit out_h5 if provided
            # (backwards compat for single video),
            # else rename based on convention
            if out_h5_path and len(videos) == 1:
                target_path = out_h5_path
            else:
                stem_no_prefix = video_path.stem.replace("trimmed_", "")
                target_path = out_dir / f"{stem_no_prefix}_superanimal.h5"

            if src_h5.resolve() != target_path.resolve():
                shutil.copy2(src_h5, target_path)
                logger.info(f"Linked H5 output : {src_h5.name} -> {target_path.name}")

        elapsed = time.time() - t0
        logger.info(f"SUCCESS: Inference completed cleanly in {elapsed:.1f} seconds.")

    except Exception as e:
        logger.error(f"RUNTIME ERROR: Inference failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
