import argparse
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path



class FlushingStreamHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()


def setup_logging() -> None:
    """
    Configure root logger with a flushing stdout handler ONLY.
    Note: We do NOT use a FileHandler here because the parent Bash script
    is already capturing stdout and writing it to the log file using 'tee'.
    """
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    sh = FlushingStreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(sh)


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
                capture_output=True, text=True, timeout=10,
            )
            install_method = (
                f"Pip (env: {prefix})" if r.returncode == 0
                else f"Unknown (env: {prefix})"
            )
        except Exception:
            install_method = f"Unknown (env: {prefix})"

    cuda_vis = os.environ.get("CUDA_VISIBLE_DEVICES", "NOT SET")
    gpu_lines = [f"CUDA_VISIBLE_DEVICES={cuda_vis}"]
    try:
        r = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=index,name,memory.total,memory.free,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0:
            for row in r.stdout.strip().splitlines():
                idx, name, mem_total, mem_free, util = [c.strip() for c in row.split(",")]
                gpu_lines.append(
                    f"  GPU {idx}: {name} | mem {mem_free}/{mem_total} MiB free | util {util}%"
                )
    except FileNotFoundError:
        gpu_lines.append("  nvidia-smi not found — running on CPU?")
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



def run_dlc_inference_subprocess(
    videos: list[Path],
    out_dir: Path,
    batch_id: str,
    superanimal: str,
    video_adapt: bool,
    out_h5: Path | None,
) -> None:
    """
    Runs DLC inference in a child process so its stdout/stderr can be
    streamed line-by-line into our logger in real time.
    """
    cmd = [
        sys.executable, "-u",                                         
        __file__,
        "--_subprocess",                                                        
        "--out_dir",    str(out_dir),
        "--batch_id",   batch_id,
        "--superanimal", superanimal,
        "--videos",     *[str(v) for v in videos],
    ]
    if video_adapt:
        cmd.append("--video_adapt")
    if out_h5:
        cmd += ["--out_h5", str(out_h5)]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    logger.info(f"Spawning DLC subprocess: {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,                             
        text=True,
        bufsize=1,                                 
        env=env,
    )

    for line in proc.stdout:
        line = line.rstrip("\n")
        if line:
                                                                        
                                                                         
            print(f"[dlc-worker] {line}", flush=True)

    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"DLC subprocess exited with code {proc.returncode}")



def run_inference(args) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_h5_path = Path(args.out_h5) if args.out_h5 else None
    if out_h5_path:
        out_h5_path.parent.mkdir(parents=True, exist_ok=True)

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
    logger.info(f"Model            : {args.config_path or args.superanimal}")
    logger.info("=" * 60)

                               
    logger.info("Setting up working directory to route DLC outputs...")
    working_videos = []
    for video_path in videos:
        symlink_path = out_dir / video_path.name
        if not symlink_path.exists():
            try:
                os.symlink(video_path.resolve(), symlink_path)
            except OSError:
                                                                                
                import shutil
                shutil.copy2(video_path, symlink_path)
        working_videos.append(symlink_path)

    logger.info("Loading DeepLabCut (this may take a moment)...")
    import deeplabcut
    logger.info("DeepLabCut loaded.")

    t0 = time.time()

    if args.config_path:
        logger.info("Starting inference in Standard Project Mode...")
        deeplabcut.analyze_videos(
            args.config_path,
            [str(v) for v in working_videos],                   
            videotype=working_videos[0].suffix.lstrip(".") or "mp4",
            save_as_csv=True,
            destfolder=str(out_dir),
        )
    else:
        logger.info(
            f"Starting SuperAnimal inference ({args.superanimal}) | "
            f"video_adapt={args.video_adapt}..."
        )
        deeplabcut.video_inference_superanimal(
            [str(v) for v in working_videos],                   
            args.superanimal,
            videotype=working_videos[0].suffix.lstrip(".") or "mp4",
            video_adapt=args.video_adapt,
        )

    logger.info("Locating target H5 files...")
                                                             
    for sym_path, orig_path in zip(working_videos, videos):
        h5_candidates = sorted(out_dir.glob(f"{sym_path.stem}*.h5"))
            
        if not h5_candidates:
            raise FileNotFoundError(
                f"No H5 found in {out_dir} for {sym_path.stem} — "
                f"DLC may have failed silently."
            )

        src_h5 = max(h5_candidates, key=lambda p: p.stat().st_mtime)

        if out_h5_path and len(videos) == 1:
            target_path = out_h5_path
        else:
            stem_no_prefix = orig_path.stem.replace("trimmed_", "")
            target_path = out_dir / f"{stem_no_prefix}_superanimal.h5"

        if src_h5.resolve() != target_path.resolve():
            import shutil
            shutil.copy2(src_h5, target_path)
            logger.info(f"Linked H5: {src_h5.name} -> {target_path.name}")

                              
    for sym_path in working_videos:
        if sym_path.exists():
            sym_path.unlink()

    elapsed = time.time() - t0
    logger.info(f"SUCCESS: Inference completed in {elapsed:.1f}s.")

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run DLC inference on a trimmed video or batch of videos.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--videos",     nargs="+", help="Path(s) to video file(s).")
    grp.add_argument("--video_dir",  help="Directory containing video files.")

    p.add_argument("--out_dir",  required=True, help="Directory for DLC outputs.")
    p.add_argument("--batch_id", required=True, help="Batch ID for log file naming.")
    p.add_argument("--out_h5",   required=False, help="Explicit destination for single-video H5.")

    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--superanimal", default="superanimal_topviewmouse", metavar="MODEL")
    mode.add_argument("--config_path", help="DLC project config.yaml (standard mode).")

    p.add_argument("--video_adapt", action="store_true",
                   help="(SuperAnimal only) Enable unsupervised video adaptation.")

                                                                       
    p.add_argument("--_subprocess", action="store_true", help=argparse.SUPPRESS)
    return p


def main():
    args = build_parser().parse_args()

    if args.video_dir:
        videos = list(Path(args.video_dir).glob("*.mp4"))
        if not videos:
            print(f"FATAL: No .mp4 files in {args.video_dir}", file=sys.stderr)
            sys.exit(1)
        args.videos = [str(v) for v in videos]

    out_dir  = Path(args.out_dir)
    
    setup_logging()

                                                                   
    if not args._subprocess:
        log_file = out_dir.parent.parent / "logs" / args.batch_id / "dlc_inference_log.txt"
        logger.info(f"Bash is managing logs to: {log_file}")

    if args._subprocess:
                                                                 
        run_inference(args)
    else:
                                                                        
        log_environment()
        try:
            run_dlc_inference_subprocess(
                videos=[Path(v) for v in args.videos],
                out_dir=out_dir,
                batch_id=args.batch_id,
                superanimal=args.superanimal,
                video_adapt=args.video_adapt,
                out_h5=Path(args.out_h5) if args.out_h5 else None,
            )
        except Exception as e:
            logger.error(f"RUNTIME ERROR: {e}", exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    main()