"""
Local staging directory validator.

Walks a local directory, records each file's path, size, and SHA-256 hash,
and writes a manifest CSV.  Can also re-validate an existing manifest to
detect corruption or missing files.

Usage:
    # Build a new manifest
    python src/ingest/validate_staging.py \
        --staging-dir staging/ \
        --manifest staging/_logs/manifest.csv

    # Re-validate an existing manifest
    python src/ingest/validate_staging.py \
        --staging-dir staging/ \
        --manifest staging/_logs/manifest.csv \
        --validate
"""

import argparse
import csv
import hashlib
import sys
from datetime import datetime
from pathlib import Path

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB
MANIFEST_COLUMNS = ["file_path", "file_name", "size_bytes", "sha256", "recorded_at"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(staging_dir: Path, manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(
        p for p in staging_dir.rglob("*") if p.is_file() and not p.name.startswith(".")
    )

    if not files:
        print(f"No files found in {staging_dir}.")
        return

    now = datetime.now().isoformat()
    rows = []
    for fp in files:
        size = fp.stat().st_size
        print(f"  Hashing {fp.name} ({size / 1e6:.1f} MB) ...")
        sha = sha256_file(fp)
        rows.append(
            {
                "file_path": str(fp),
                "file_name": fp.name,
                "size_bytes": size,
                "sha256": sha,
                "recorded_at": now,
            }
        )

    with open(manifest_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nManifest written: {manifest_path}  ({len(rows)} file(s))")


def validate_manifest(staging_dir: Path, manifest_path: Path) -> None:
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}")
        sys.exit(1)

    with open(manifest_path, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("Manifest is empty — nothing to validate.")
        return

    errors = []
    for row in rows:
        fp = Path(row["file_path"])
        expected_size = int(row["size_bytes"])
        expected_sha = row["sha256"]

        if not fp.exists():
            errors.append(f"MISSING: {fp}")
            continue

        actual_size = fp.stat().st_size
        if actual_size != expected_size:
            errors.append(
                f"SIZE MISMATCH: {fp.name} "
                f"(expected {expected_size}, got {actual_size})"
            )
            continue

        actual_sha = sha256_file(fp)
        if actual_sha != expected_sha:
            errors.append(
                f"SHA256 MISMATCH: {fp.name} "
                f"(expected {expected_sha[:16]}…, got {actual_sha[:16]}…)"
            )
        else:
            print(f"  OK: {fp.name}")

    if errors:
        print(f"\nVALIDATION FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print(f"\nAll {len(rows)} file(s) validated successfully.")


def main():
    parser = argparse.ArgumentParser(
        description="Build or validate a file-integrity manifest for the staging directory."
    )
    parser.add_argument(
        "--staging-dir", required=True, help="Path to the local staging directory."
    )
    parser.add_argument(
        "--manifest", required=True, help="Path to the manifest CSV file."
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Re-validate an existing manifest instead of building a new one.",
    )
    args = parser.parse_args()

    staging = Path(args.staging_dir)
    manifest = Path(args.manifest)

    if not staging.exists():
        print(f"ERROR: Staging directory does not exist: {staging}")
        sys.exit(1)

    if args.validate:
        print(f"Validating manifest: {manifest}")
        validate_manifest(staging, manifest)
    else:
        print(f"Building manifest for: {staging}")
        build_manifest(staging, manifest)


if __name__ == "__main__":
    main()
