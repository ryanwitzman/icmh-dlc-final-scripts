"""
h5_to_csv.py
------------
Convert a DLC .h5 output file to a flat CSV with consistent headers and units.

DLC's native H5 has a 3-level MultiIndex column structure:
    (scorer, bodypart, coord)  →  e.g. (DLC_resnet50_..., nose, x)

This script flattens that to one row per frame with columns:
    frame, nose_x, nose_y, nose_likelihood, ear_left_x, ...

Units:
    x, y        → pixels (integer-rounded)
    likelihood  → float [0.0 – 1.0]
    frame       → 0-based integer frame index

Usage:
    python h5_to_csv.py \
        --h5 ../outputs/dlc_results/VIDEO_superanimal.h5 \
        --out_csv ../outputs/postprocessed/VIDEO.csv \
        --log_file ../outputs/logs/VIDEO_postprocess.log \
        [--pcutoff 0.6]
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def setup_logger(log_file: str) -> logging.Logger:
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("h5_to_csv")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh = logging.FileHandler(log_path)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(sh)

    return logger


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------


def load_h5(h5_path: Path, logger: logging.Logger) -> pd.DataFrame:
    """Read DLC H5 and return the raw MultiIndex DataFrame."""
    try:
        df = pd.read_hdf(h5_path)
    except Exception as e:
        raise RuntimeError(f"Failed to read H5 file: {e}") from e

    if not isinstance(df.columns, pd.MultiIndex):
        raise ValueError(
            f"Expected MultiIndex columns in {h5_path.name}, "
            f"got: {type(df.columns)}. Is this a valid DLC H5?"
        )

    levels = df.columns.nlevels
    if levels not in (3, 4):
        raise ValueError(
            f"Expected 3 or 4 column levels (scorer/bodypart/coord or "
            f"scorer/individuals/bodypart/coord), got {levels}."
        )

    scorer = df.columns.get_level_values(0).unique().tolist()
    logger.info(f"H5 loaded: {len(df)} frames, scorer(s): {scorer}")
    return df


def flatten(df: pd.DataFrame, pcutoff: float, logger: logging.Logger) -> pd.DataFrame:
    """
    Flatten DLC MultiIndex columns to a tidy single-level DataFrame.

    Supports both:
      - single-animal: (scorer, bodypart, coord)
      - multi-animal:  (scorer, individuals, bodypart, coord)

    Output columns: frame, <bodypart>_x, <bodypart>_y, <bodypart>_likelihood
    Low-confidence x/y values (likelihood < pcutoff) are set to NaN.
    """
    nlevels = df.columns.nlevels

    if nlevels == 3:
        # Single-animal: drop scorer level, keep (bodypart, coord)
        df.columns = df.columns.droplevel(0)
        bodyparts = df.columns.get_level_values(0).unique().tolist()

    elif nlevels == 4:
        # Multi-animal: drop scorer level, keep (individual, bodypart, coord)
        df.columns = df.columns.droplevel(0)
        # Flatten individual+bodypart into a single label
        individuals = df.columns.get_level_values(0).unique().tolist()
        logger.info(f"Multi-animal H5, individuals: {individuals}")
        # Collapse (individual, bodypart) → "individual_bodypart"
        new_cols = [
            "_".join(filter(None, [ind, bp, coord])) for ind, bp, coord in df.columns
        ]
        df.columns = new_cols
        # Rebuild as if single-level for uniform processing below
        rows = {"frame": range(len(df))}
        out = pd.DataFrame(rows)
        # group columns by (individual, bodypart) pairs
        processed_pairs: set = set()
        for col in df.columns:
            parts = col.rsplit("_", 1)
            if len(parts) != 2 or parts[1] not in ("x", "y", "likelihood"):
                continue
            prefix = parts[0]
            if prefix in processed_pairs:
                continue
            processed_pairs.add(prefix)
            x_col = f"{prefix}_x"
            y_col = f"{prefix}_y"
            like_col = f"{prefix}_likelihood"
            if not all(c in df.columns for c in [x_col, y_col, like_col]):
                logger.warning(
                    f"  Skipping '{prefix}': missing x/y/likelihood columns."
                )
                continue
            likelihood = df[like_col].astype(float)
            mask = likelihood < pcutoff
            out[x_col] = df[x_col].round(1).where(~mask)
            out[y_col] = df[y_col].round(1).where(~mask)
            out[like_col] = likelihood.round(4)
        n_bp = len(processed_pairs)
        logger.info(f"Flattened {n_bp} bodypart(s)/individual(s).")
        return out

    # --- Single-animal path ---
    bodyparts = df.columns.get_level_values(0).unique().tolist()
    logger.info(f"Bodyparts ({len(bodyparts)}): {bodyparts}")

    rows: dict = {"frame": range(len(df))}
    skipped = []
    for bp in bodyparts:
        try:
            bp_df = df[bp]
        except KeyError:
            skipped.append(bp)
            continue

        if not {"x", "y", "likelihood"}.issubset(bp_df.columns):
            skipped.append(bp)
            continue

        likelihood = bp_df["likelihood"].astype(float)
        mask = likelihood < pcutoff  # True where confidence is too low

        rows[f"{bp}_x"] = bp_df["x"].round(1).where(~mask)
        rows[f"{bp}_y"] = bp_df["y"].round(1).where(~mask)
        rows[f"{bp}_likelihood"] = likelihood.round(4)

    if skipped:
        logger.warning(f"Skipped bodyparts (missing coords): {skipped}")

    out = pd.DataFrame(rows)
    logger.info(
        f"Flattened to {len(out)} frames × {len(out.columns)} columns "
        f"(pcutoff={pcutoff})."
    )
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Convert DLC H5 output to flat CSV with consistent headers.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--h5", required=True, help="Path to DLC .h5 output file.")
    parser.add_argument(
        "--out_csv", required=True, help="Destination path for the output CSV."
    )
    parser.add_argument(
        "--log_file", required=True, help="Log file path (managed by Snakemake)."
    )
    parser.add_argument(
        "--pcutoff",
        type=float,
        default=0.6,
        help="Likelihood threshold: x/y set to NaN below this value.",
    )
    args = parser.parse_args()

    logger = setup_logger(args.log_file)

    h5_path = Path(args.h5)
    csv_path = Path(args.out_csv)

    if not h5_path.exists():
        logger.error(f"H5 file not found: {h5_path}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info(f"Input H5  : {h5_path}")
    logger.info(f"Output CSV: {csv_path}")
    logger.info(f"p-cutoff  : {args.pcutoff}")
    logger.info("=" * 60)

    try:
        df_raw = load_h5(h5_path, logger)
        df_out = flatten(df_raw, args.pcutoff, logger)

        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(csv_path, index=False)

        logger.info(f"SUCCESS: wrote {len(df_out)} rows to {csv_path}")

    except Exception as e:
        logger.error(f"FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
