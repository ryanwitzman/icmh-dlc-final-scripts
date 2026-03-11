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
        [--pcutoff 0.6] \
        [--expected_bodyparts nose ear_left ear_right] \
        [--expected_frames 1800]
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd




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




def validate_h5(
    df: pd.DataFrame,
    logger: logging.Logger,
    *,
    expected_bodyparts: list[str] | None = None,
    expected_frames: int | None = None,
    pcutoff: float = 0.6,
) -> None:
    """
    Run pre-conversion checks on the raw MultiIndex DataFrame.
    Raises ValueError on the first failed check; all errors are logged
    before raising so the log captures the full picture.

    Checks
    ------
    1. Expected bodyparts present (if --expected_bodyparts supplied).
    2. Frame count matches video (if --expected_frames supplied).
    3. Likelihood values are in [0.0, 1.0].
    4. No bodypart is all-NaN after applying pcutoff.
    """
    errors: list[str] = []
    nlevels = df.columns.nlevels


    bp_level = 1 if nlevels == 3 else 2
    present_bodyparts = df.columns.get_level_values(bp_level).unique().tolist()


    if expected_bodyparts:
        missing = sorted(set(expected_bodyparts) - set(present_bodyparts))
        if missing:
            errors.append(
                f"Missing expected bodypart(s): {missing}. "
                f"Present: {present_bodyparts}"
            )
        else:
            logger.info(
                f"[validate] Bodyparts OK — all {len(expected_bodyparts)} "
                f"expected bodypart(s) present."
            )


    if expected_frames is not None:
        actual = len(df)
        if actual != expected_frames:
            errors.append(
                f"Frame count mismatch: H5 has {actual} frame(s), "
                f"expected {expected_frames}."
            )
        else:
            logger.info(f"[validate] Frame count OK — {actual} frame(s).")


    coord_level = nlevels - 1
    like_mask = df.columns.get_level_values(coord_level) == "likelihood"
    like_cols = df.columns[like_mask]

    if len(like_cols) == 0:
        errors.append("No likelihood columns found — is this a valid DLC H5?")
    else:
        like_df = df[like_cols].astype(float)
        out_of_range = (like_df < 0.0) | (like_df > 1.0)
        bad_cols = [str(c) for c in like_cols[out_of_range.any(axis=0)]]
        if bad_cols:

            sample = bad_cols[:5]
            extra = f" (and {len(bad_cols) - 5} more)" if len(bad_cols) > 5 else ""
            errors.append(
                f"Likelihood values outside [0, 1] in column(s): " f"{sample}{extra}."
            )
        else:
            logger.info(
                f"[validate] Likelihood range OK — all {len(like_cols)} "
                f"likelihood column(s) in [0, 1]."
            )


    all_nan_bps: list[str] = []
    for bp in present_bodyparts:
        try:

            if nlevels == 3:
                like_series = df.xs("likelihood", level=2, axis=1)[bp]
            else:

                like_series = df.xs("likelihood", level=3, axis=1)[bp]
        except KeyError:
            continue

        passing = (like_series.astype(float) >= pcutoff).sum()
        if passing == 0:
            all_nan_bps.append(bp)

    if all_nan_bps:
        errors.append(
            f"Bodypart(s) with zero frames above pcutoff={pcutoff}: "
            f"{sorted(all_nan_bps)}. Output would be entirely NaN."
        )
    else:
        logger.info(
            f"[validate] pcutoff OK — all bodypart(s) have at least one "
            f"frame above pcutoff={pcutoff}."
        )


    if errors:
        logger.error(f"[validate] Validation FAILED with {len(errors)} error(s):")
        for i, msg in enumerate(errors, 1):
            logger.error(f"  [{i}] {msg}")
        raise ValueError(
            f"H5 validation failed ({len(errors)} error(s)); see log for details."
        )

    logger.info("[validate] All checks passed.")




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

        df.columns = df.columns.droplevel(0)
        bodyparts = df.columns.get_level_values(0).unique().tolist()

    elif nlevels == 4:

        df.columns = df.columns.droplevel(0)

        individuals = df.columns.get_level_values(0).unique().tolist()
        logger.info(f"Multi-animal H5, individuals: {individuals}")

        new_cols = [
            "_".join(filter(None, [ind, bp, coord])) for ind, bp, coord in df.columns
        ]
        df.columns = new_cols

        rows = {"frame": range(len(df))}
        out = pd.DataFrame(rows)

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
        mask = likelihood < pcutoff

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
    parser.add_argument(
        "--expected_bodyparts",
        nargs="+",
        default=None,
        metavar="BP",
        help=(
            "Space-separated list of bodypart names that must be present in the H5. "
            "Omit to skip this check."
        ),
    )
    parser.add_argument(
        "--expected_frames",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Exact number of frames the H5 must contain (e.g. from your video). "
            "Omit to skip this check."
        ),
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
    if args.expected_bodyparts:
        logger.info(f"Expected bodyparts: {args.expected_bodyparts}")
    if args.expected_frames is not None:
        logger.info(f"Expected frames: {args.expected_frames}")
    logger.info("=" * 60)

    try:
        df_raw = load_h5(h5_path, logger)

        validate_h5(
            df_raw,
            logger,
            expected_bodyparts=args.expected_bodyparts,
            expected_frames=args.expected_frames,
            pcutoff=args.pcutoff,
        )

        df_out = flatten(df_raw, args.pcutoff, logger)

        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(csv_path, index=False)

        logger.info(f"SUCCESS: wrote {len(df_out)} rows to {csv_path}")

    except Exception as e:
        logger.error(f"FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
