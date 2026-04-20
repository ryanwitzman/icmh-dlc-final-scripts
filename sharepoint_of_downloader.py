#!/usr/bin/env python3
"""
SharePoint OneDrive 'OF' Video Downloader — two-mode script.

MODE 1: login (run on your LAPTOP where Chrome exists)
    Opens Chrome, logs into IU SSO + Duo, then saves cookies + resolved
    SharePoint site info to a JSON file you copy to Quartz.

        python sharepoint_of_downloader.py login --out sp_auth.json

MODE 2: download (run on QUARTZ — no browser needed)
    Reads the JSON, walks the SharePoint tree via REST API, downloads
    every video containing 'OF' to the staging dir.

        python sharepoint_of_downloader.py download --auth sp_auth.json
        python sharepoint_of_downloader.py download --auth sp_auth.json --dry-run

Workflow:
    # on laptop (one-time, cookies last a few hours to ~a day):
    pip install selenium requests
    python sharepoint_of_downloader.py login --out sp_auth.json
    scp sp_auth.json rwitzman@quartz.uits.iu.edu:/N/project/msk_dl/icmh-dlc-final-scripts/

    # on quartz:
    module load conda/25.3.0 && conda activate icmh-dlc-310
    python sharepoint_of_downloader.py download --auth sp_auth.json

If SharePoint cookies expire mid-download, just re-run `login` on your laptop
and re-copy the JSON — the `download` command will skip already-completed files.
"""

import argparse
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

import requests


# ---------- CONFIG ----------
SHAREPOINT_URL = (
    "https://indiana.sharepoint.com/:f:/s/msteams_9c5cec-KacenaLabAllResearch/"
    "IgAHfdHIuAA_Q4e56J1m68zgAf_emryx-i7J_12ejrw7X3A"
)
IU_USERNAME_DEFAULT = "rwitzman"
STAGING_DIR_DEFAULT = "/N/project/msk_dl/icmh-dlc-final-scripts/staging"
MATCH_TOKEN = "OF"  # only download files with this token in the name
VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v", ".mpeg", ".mpg", ".webm")
# ----------------------------


def log(msg, level="INFO"):
    colors = {
        "INFO": "\033[36m",
        "OK":   "\033[32m",
        "WARN": "\033[33m",
        "ERR":  "\033[31m",
        "STEP": "\033[35m",
    }
    reset = "\033[0m"
    c = colors.get(level, "")
    ts = time.strftime("%H:%M:%S")
    print(f"{c}[{ts}] [{level}]{reset} {msg}", flush=True)


def human_size(n):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


# ============================================================
# MODE 1: LOGIN (run on laptop, requires Selenium + Chrome)
# ============================================================

def mode_login(args):
    try:
        from selenium import webdriver
        from selenium.common.exceptions import (
            NoSuchElementException, TimeoutException, WebDriverException,
        )
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError:
        log("Selenium not installed. Run: pip install selenium requests", "ERR")
        sys.exit(1)

    username = args.username or IU_USERNAME_DEFAULT
    password = os.environ.get("IU_PASSWORD") or getpass.getpass(f"IU password for {username}: ")

    # Build driver — Selenium Manager handles chromedriver automatically.
    opts = Options()
    opts.add_argument("--window-size=1400,900")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    log("Starting Chrome (Selenium Manager will fetch chromedriver if needed)...", "STEP")
    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )

    try:
        log("Opening SharePoint URL (will redirect to IU login)...", "STEP")
        driver.get(SHAREPOINT_URL)

        wait = WebDriverWait(driver, 60)

        # IU CAS login
        try:
            user_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
            log("IU CAS login page loaded.", "INFO")
            user_field.clear(); user_field.send_keys(username)
            pw_field = driver.find_element(By.ID, "password")
            pw_field.clear(); pw_field.send_keys(password)
            try:
                btn = driver.find_element(By.NAME, "submit")
            except NoSuchElementException:
                btn = driver.find_element(
                    By.CSS_SELECTOR, "button[type='submit'], input[type='submit']"
                )
            btn.click()
            log("Submitted credentials. Waiting for Duo...", "OK")
        except TimeoutException:
            log("No CAS page — maybe already signed in.", "WARN")

        # Duo loop: print code, handle trust/stay-signed-in, wait for SharePoint.
        log("Looking for Duo verification code (will print to terminal)...", "STEP")
        duo_code_printed = False
        duo_start = time.time()
        duo_timeout = 240

        def try_find_duo_code():
            selectors = [
                ".verification-code",
                ".passcode",
                "[class*='verification-code']",
                "[class*='verificationCode']",
                "[data-testid='verification-code']",
            ]
            for sel in selectors:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    txt = el.text.strip()
                    if txt and re.search(r"\d{2,}", txt):
                        return txt
                except NoSuchElementException:
                    continue
            return None

        while time.time() - duo_start < duo_timeout:
            cur = driver.current_url.lower()
            if "sharepoint.com" in cur and "login" not in cur and "adfs" not in cur:
                log("Reached SharePoint.", "OK")
                break

            if not duo_code_printed:
                code = try_find_duo_code()
                if code:
                    print("\n" + "=" * 50)
                    print(f"  DUO VERIFICATION CODE: {code}")
                    print("  Enter this in your Duo Mobile app.")
                    print("=" * 50 + "\n", flush=True)
                    duo_code_printed = True

            for xp in [
                "//button[contains(., 'Yes, trust browser')]",
                "//button[contains(., 'Trust browser')]",
                "//button[contains(., 'Yes, this is my device')]",
            ]:
                try:
                    driver.find_element(By.XPATH, xp).click()
                    log("Clicked 'Trust browser'.", "INFO")
                    break
                except NoSuchElementException:
                    pass

            try:
                driver.find_element(By.ID, "idSIButton9").click()
                log("Clicked 'Stay signed in'.", "INFO")
            except NoSuchElementException:
                pass

            time.sleep(1.5)
        else:
            log("Timed out waiting for Duo approval.", "ERR")
            sys.exit(1)

        # Let SharePoint finish loading & resolve the folder path.
        log("Waiting for SharePoint to settle and resolve the folder...", "STEP")
        time.sleep(5)

        resolved_url = driver.current_url
        log(f"Resolved URL: {resolved_url}", "INFO")

        parsed = urlparse(resolved_url)
        qs = parse_qs(parsed.query)

        folder_path = None
        for key in ("id", "RootFolder"):
            if key in qs:
                folder_path = unquote(qs[key][0])
                break
        if not folder_path:
            try:
                folder_path = driver.execute_script(
                    "return _spPageContextInfo && _spPageContextInfo.serverRequestPath;"
                )
            except Exception:
                pass
        if not folder_path:
            log("Could not auto-detect folder path. Paste the URL from the address bar:", "WARN")
            folder_path = input("Paste server-relative folder path (/sites/.../Shared Documents/...): ").strip()

        site_match = re.match(r"^(/sites/[^/]+|/teams/[^/]+)", folder_path)
        if site_match:
            site_path = site_match.group(1)
        else:
            site_path = driver.execute_script("return _spPageContextInfo.webServerRelativeUrl;")

        site_url = f"{parsed.scheme}://{parsed.netloc}{site_path}"

        # Extract cookies
        cookies = driver.get_cookies()
        user_agent = driver.execute_script("return navigator.userAgent")

        out = {
            "site_url": site_url,
            "root_folder": folder_path,
            "user_agent": user_agent,
            "cookies": cookies,
            "saved_at": time.time(),
        }
        out_path = Path(args.out)
        out_path.write_text(json.dumps(out, indent=2))
        try:
            os.chmod(out_path, 0o600)
        except OSError:
            pass

        log(f"Saved auth to {out_path}", "OK")
        log(f"  Site URL:    {site_url}", "OK")
        log(f"  Root folder: {folder_path}", "OK")
        log(f"  Cookies:     {len(cookies)}", "OK")
        log("Copy this file to Quartz and run:", "INFO")
        log(f"  python sharepoint_of_downloader.py download --auth {out_path.name}", "INFO")

    finally:
        try:
            driver.quit()
        except Exception:
            pass


# ============================================================
# MODE 2: DOWNLOAD (run on Quartz, no browser needed)
# ============================================================

def build_session_from_auth(auth):
    s = requests.Session()
    for c in auth["cookies"]:
        s.cookies.set(c["name"], c["value"], domain=c.get("domain"))
    s.headers.update({
        "User-Agent": auth.get("user_agent", "Mozilla/5.0"),
        "Accept": "application/json;odata=verbose",
    })
    return s


def sp_get_folder_contents(session, site_url, server_relative_path):
    esc = server_relative_path.replace("'", "''")
    base = f"{site_url}/_api/web/GetFolderByServerRelativeUrl('{esc}')"

    files, folders = [], []

    files_url = f"{base}/Files?$top=5000&$select=Name,ServerRelativeUrl,Length,TimeLastModified"
    r = session.get(files_url, headers={"Accept": "application/json;odata=verbose"})
    if r.status_code == 401 or r.status_code == 403:
        raise RuntimeError(
            f"Auth failed ({r.status_code}). Your cookies have probably expired — "
            "re-run the `login` step on your laptop and copy the new JSON over."
        )
    if r.status_code != 200:
        log(f"Failed to list files in {server_relative_path} ({r.status_code})", "ERR")
        log(r.text[:400], "ERR")
        return [], []
    try:
        data = r.json()["d"]["results"]
    except Exception:
        log(f"Could not parse file list JSON for {server_relative_path}", "ERR")
        return [], []
    for f in data:
        files.append({
            "name": f["Name"],
            "server_rel": f["ServerRelativeUrl"],
            "size": int(f.get("Length", 0) or 0),
        })

    folders_url = f"{base}/Folders?$top=5000&$select=Name,ServerRelativeUrl"
    r = session.get(folders_url, headers={"Accept": "application/json;odata=verbose"})
    if r.status_code != 200:
        log(f"Failed to list folders in {server_relative_path} ({r.status_code})", "ERR")
        return files, []
    for f in r.json()["d"]["results"]:
        if f["Name"] in ("Forms", "_catalogs", "_private"):
            continue
        folders.append({"name": f["Name"], "server_rel": f["ServerRelativeUrl"]})

    return files, folders


def walk_sharepoint(session, site_url, root_path):
    stack = [root_path]
    visited = set()
    total_files = 0
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        log(f"Listing: {current}", "INFO")
        files, folders = sp_get_folder_contents(session, site_url, current)
        for f in files:
            total_files += 1
            yield f
        for sub in folders:
            stack.append(sub["server_rel"])
    log(f"Walk complete. Saw {total_files} files across {len(visited)} folders.", "OK")


def is_target_video(name):
    lower = name.lower()
    if not lower.endswith(VIDEO_EXTS):
        return False
    stem = re.sub(r"\.[^.]+$", "", name)
    return bool(re.search(r"(^|[^A-Za-z])OF([^A-Za-z]|$)", stem))


def download_file(session, site_url, file_info, staging_dir):
    name = file_info["name"]
    src_path = file_info["server_rel"]
    expected = file_info["size"]
    dest = staging_dir / name

    if dest.exists():
        try:
            if expected and dest.stat().st_size == expected:
                log(f"SKIP (already present, size matches): {name}", "WARN")
                return "skipped"
            else:
                log(f"Exists but size differs, re-downloading: {name}", "WARN")
        except OSError:
            pass

    esc = src_path.replace("'", "''")
    dl_url = f"{site_url}/_api/web/GetFileByServerRelativeUrl('{esc}')/$value"

    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with session.get(dl_url, stream=True, timeout=300) as r:
            if r.status_code != 200:
                log(f"Download failed for {name}: HTTP {r.status_code}", "ERR")
                return "failed"
            total = int(r.headers.get("Content-Length", expected or 0))
            downloaded = 0
            last_print = 0
            t0 = time.time()
            with open(tmp, "wb") as out:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    out.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if now - last_print >= 0.5 or downloaded == total:
                        pct = (downloaded / total * 100) if total else 0
                        speed = downloaded / (now - t0 + 1e-9)
                        bar_w = 30
                        filled = int(bar_w * pct / 100) if total else 0
                        bar = "#" * filled + "-" * (bar_w - filled)
                        sys.stdout.write(
                            f"\r    {name[:40]:<40} [{bar}] {pct:5.1f}%  "
                            f"{human_size(downloaded)}/{human_size(total) if total else '?'}  "
                            f"{human_size(speed)}/s   "
                        )
                        sys.stdout.flush()
                        last_print = now
            sys.stdout.write("\n")
        tmp.rename(dest)
        log(f"Downloaded: {name} ({human_size(dest.stat().st_size)})", "OK")
        return "downloaded"
    except Exception as e:
        log(f"Error downloading {name}: {e}", "ERR")
        if tmp.exists():
            try: tmp.unlink()
            except OSError: pass
        return "failed"


def mode_download(args):
    auth_path = Path(args.auth)
    if not auth_path.exists():
        log(f"Auth file not found: {auth_path}", "ERR")
        log("Run the `login` mode on your laptop first to create it.", "ERR")
        sys.exit(1)

    auth = json.loads(auth_path.read_text())
    age_hours = (time.time() - auth.get("saved_at", 0)) / 3600
    log(f"Loaded auth from {auth_path} (age: {age_hours:.1f}h)", "INFO")
    if age_hours > 12:
        log("Auth is >12h old — if it fails, re-run `login` on your laptop.", "WARN")

    site_url = auth["site_url"]
    root_folder = auth["root_folder"]
    session = build_session_from_auth(auth)

    staging_dir = Path(args.staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    log(f"Staging dir: {staging_dir}", "INFO")
    log(f"Site URL:    {site_url}", "INFO")
    log(f"Root folder: {root_folder}", "INFO")

    # Quick auth sanity check
    log("Testing auth...", "STEP")
    test = session.get(
        f"{site_url}/_api/web/GetFolderByServerRelativeUrl('{root_folder.replace(chr(39), chr(39)*2)}')",
        headers={"Accept": "application/json;odata=verbose"},
    )
    if test.status_code != 200:
        log(f"Auth test failed: HTTP {test.status_code}", "ERR")
        log(test.text[:400], "ERR")
        log("Your cookies have probably expired. Re-run `login` on your laptop.", "ERR")
        sys.exit(1)
    log("Auth OK.", "OK")

    log("Crawling SharePoint tree for matching videos...", "STEP")
    matches = []
    for f in walk_sharepoint(session, site_url, root_folder):
        if is_target_video(f["name"]):
            matches.append(f)
            log(f"  MATCH: {f['server_rel']}  ({human_size(f['size'])})", "OK")

    log(f"Found {len(matches)} 'OF' video(s) to consider.", "STEP")

    if args.dry_run:
        log("Dry run — exiting without downloading.", "INFO")
        return

    stats = {"downloaded": 0, "skipped": 0, "failed": 0}
    for i, f in enumerate(matches, 1):
        log(f"[{i}/{len(matches)}] {f['name']}", "STEP")
        result = download_file(session, site_url, f, staging_dir)
        stats[result] = stats.get(result, 0) + 1

    log(
        f"Done. Downloaded: {stats['downloaded']}, "
        f"Skipped: {stats['skipped']}, Failed: {stats['failed']}",
        "OK",
    )


# ============================================================
# CLI
# ============================================================

def main():
    ap = argparse.ArgumentParser(description="SharePoint 'OF' video downloader (two-step).")
    sub = ap.add_subparsers(dest="mode", required=True)

    lp = sub.add_parser("login", help="Interactive login on your laptop — saves cookies to JSON.")
    lp.add_argument("--out", default="sp_auth.json", help="Where to save the auth JSON.")
    lp.add_argument("--username", default=None, help=f"IU username (default: {IU_USERNAME_DEFAULT}).")

    dp = sub.add_parser("download", help="Download all OF videos using saved cookies (Quartz-friendly).")
    dp.add_argument("--auth", required=True, help="Path to auth JSON produced by `login`.")
    dp.add_argument("--staging-dir", default=STAGING_DIR_DEFAULT, help="Download destination.")
    dp.add_argument("--dry-run", action="store_true", help="List matches without downloading.")

    args = ap.parse_args()

    if args.mode == "login":
        mode_login(args)
    elif args.mode == "download":
        mode_download(args)


if __name__ == "__main__":
    main()