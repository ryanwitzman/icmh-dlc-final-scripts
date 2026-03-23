import argparse
import csv
import hashlib
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import msal
import requests
from tqdm import tqdm

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
CHUNK_SIZE = 8 * 1024 * 1024
SCOPES = [
    "https://graph.microsoft.com/Sites.Read.All",
    "https://graph.microsoft.com/Files.Read.All",
]
TOKEN_CACHE = os.path.join(os.path.expanduser("~"), ".hpc_ingest_token_cache.json")
LOG_COLUMNS = [
    "batch_id",
    "remote_path",
    "local_path",
    "size_bytes",
    "sha256_remote",
    "sha256_local",
    "transfer_start",
    "transfer_end",
    "duration_s",
    "status",
    "notes",
]


def setup_logging(log_dir: Path, batch_id: str) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{batch_id}_run.log"
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("hpc_ingest")


def get_access_token(tenant_id: str, client_id: str) -> str:
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE):
        cache.deserialize(open(TOKEN_CACHE).read())

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.PublicClientApplication(
        client_id,
        authority=authority,
        token_cache=cache,
    )

    accounts = app.get_accounts()
    result = app.acquire_token_silent(SCOPES, account=accounts[0]) if accounts else None

    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError(f"Device flow failed: {flow.get('error_description')}")
        print("\n" + flow["message"])
        print()
        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(f"Auth failed: {result.get('error_description')}")

    if cache.has_state_changed:
        with open(TOKEN_CACHE, "w") as f:
            f.write(cache.serialize())

    return result["access_token"]


def graph_get(token: str, url: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    for attempt in range(5):
        r = requests.get(url, headers=headers, timeout=60)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 10))
            logging.getLogger("hpc_ingest").warning("Rate-limited. Waiting %ds …", wait)
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Failed after retries: {url}")


def resolve_drive_and_item(token: str, sharepoint_url: str, remote_path: str):
    from urllib.parse import urlparse

    parsed = urlparse(sharepoint_url)
    host = parsed.netloc
    sp_path = parsed.path.rstrip("/")

    site_url = f"{GRAPH_BASE}/sites/{host}:{sp_path}"
    site_data = graph_get(token, site_url)
    site_id = site_data["id"]

    drives_url = f"{GRAPH_BASE}/sites/{site_id}/drives"
    drives = graph_get(token, drives_url)["value"]
    drive_id = drives[0]["id"]

    encoded = quote(remote_path)
    item_url = f"{GRAPH_BASE}/drives/{drive_id}/root:/{encoded}"
    item_data = graph_get(token, item_url)
    item_id = item_data["id"]

    return drive_id, item_id


def walk_mp4s(token: str, drive_id: str, item_id: str, logger: logging.Logger):
    url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/children"
    while url:
        data = graph_get(token, url)
        items = data.get("value", [])
        for item in items:
            if "folder" in item:
                yield from walk_mp4s(token, drive_id, item["id"], logger)
            elif item["name"].lower().endswith(".mp4"):
                fh = item.get("file", {}).get("hashes", {})
                yield {
                    "name": item["name"],
                    "remote_path": item.get("parentReference", {}).get("path", "")
                    + "/"
                    + item["name"],
                    "size": item.get("size", 0),
                    "download_url": item.get("@microsoft.graph.downloadUrl", ""),
                    "quickXorHash": fh.get("quickXorHash", ""),
                    "sha256remote": fh.get("sha256Hash", "").lower(),
                }
        url = data.get("@odata.nextLink")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_size(path: Path, expected: int) -> bool:
    return path.stat().st_size == expected


def download_file(url: str, dest: Path, size: int, logger: logging.Logger) -> float:
    dest.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f, tqdm(
            total=size,
            unit="B",
            unit_scale=True,
            desc=dest.name,
            leave=False,
        ) as bar:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)
                bar.update(len(chunk))
    return time.time() - t0


class BatchLog:
    def __init__(self, path: Path):
        self.path = path
        self._rows: list[dict] = []
        if path.exists():
            with open(path, newline="") as f:
                self._rows = list(csv.DictReader(f))

    def add(self, row: dict):
        self._rows.append(row)
        with open(self.path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
            w.writeheader()
            w.writerows(self._rows)

    def summary(self) -> dict:
        total = len(self._rows)
        ok = sum(1 for r in self._rows if r["status"] == "OK")
        failed = total - ok
        sizes = sum(int(r["size_bytes"] or 0) for r in self._rows)
        return {"total": total, "ok": ok, "failed": failed, "total_bytes": sizes}


def main():
    parser = argparse.ArgumentParser(description="HPC SharePoint video ingest")
    parser.add_argument("--sharepoint-url", required=True)
    parser.add_argument(
        "--remote-path", required=True, help="Folder path inside the document library"
    )
    parser.add_argument(
        "--staging-dir", required=True, help="Local HPC staging directory"
    )
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--client-id", required=True)

    parser.add_argument(
        "--batch-id", default=None, help="Unique batch label (default: timestamp)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip files already present in staging",
    )
    args = parser.parse_args()

    batch_id = args.batch_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    staging = Path(args.staging_dir)
    log_dir = staging / "_logs"
    logger = setup_logging(log_dir, batch_id)
    batch_log = BatchLog(log_dir / f"{batch_id}_manifest.csv")

    staging.mkdir(parents=True, exist_ok=True)
    logger.info("Staging directory: %s", staging)
    logger.info("Batch ID: %s", batch_id)

    logger.info("Authenticating with Microsoft Graph …")
    token = get_access_token(args.tenant_id, args.client_id)

    logger.info("Resolving SharePoint path: %s", args.remote_path)
    drive_id, item_id = resolve_drive_and_item(
        token, args.sharepoint_url, args.remote_path
    )

    logger.info("Walking remote tree for .mp4 files …")
    for file_info in walk_mp4s(token, drive_id, item_id, logger):
        rel = Path(file_info["remote_path"].lstrip("/"))
        dest = staging / rel

        row = {c: "" for c in LOG_COLUMNS}
        row.update(
            {
                "batch_id": batch_id,
                "remote_path": file_info["remote_path"],
                "local_path": str(dest),
                "size_bytes": file_info["size"],
            }
        )

        if args.skip_existing and dest.exists():
            logger.info("SKIP (exists): %s", rel)
            row["status"] = "SKIPPED"
            batch_log.add(row)
            continue

        logger.info("Downloading: %s  (%.1f MB)", rel, file_info["size"] / 1e6)

        t_start = datetime.now(timezone.utc)
        row["transfer_start"] = t_start.isoformat()

        try:
            elapsed = download_file(
                file_info["download_url"], dest, file_info["size"], logger
            )
        except Exception as exc:
            logger.error("Download FAILED: %s — %s", rel, exc)
            row["status"] = "DOWNLOAD_FAILED"
            row["notes"] = str(exc)
            batch_log.add(row)
            continue

        t_end = datetime.now(timezone.utc)
        row["transfer_end"] = t_end.isoformat()
        row["duration_s"] = f"{elapsed:.1f}"

        issues = []

        if not validate_size(dest, file_info["size"]):
            issues.append(
                f"size mismatch (expected {file_info['size']}, "
                f"got {dest.stat().st_size})"
            )

        local_sha = sha256_file(dest)
        row["sha256_local"] = local_sha
        if file_info["sha256remote"]:
            row["sha256_remote"] = file_info["sha256remote"]
            if local_sha != file_info["sha256remote"]:
                issues.append(
                    f"sha256 mismatch (remote={file_info['sha256remote']}, "
                    f"local={local_sha})"
                )
        else:
            row["sha256_remote"] = "N/A (not provided by API)"

        if issues:
            row["status"] = "CORRUPT"
            row["notes"] = "; ".join(issues)
            logger.error("INTEGRITY FAILURE: %s — %s", rel, row["notes"])
            dest.rename(dest.with_suffix(".CORRUPT"))
        else:
            row["status"] = "OK"
            logger.info(
                "OK  %.1f MB in %.1fs — %s", file_info["size"] / 1e6, elapsed, rel
            )

        batch_log.add(row)

    s = batch_log.summary()
    logger.info("═" * 60)
    logger.info("BATCH COMPLETE  id=%s", batch_id)
    logger.info(
        "  Files   : %d total | %d OK | %d failed/corrupt",
        s["total"],
        s["ok"],
        s["failed"],
    )
    logger.info("  Data    : %.2f GB", s["total_bytes"] / 1e9)
    logger.info("  Manifest: %s", batch_log.path)
    logger.info("═" * 60)

    sys.exit(0 if s["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
