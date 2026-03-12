import yaml
from pathlib import Path


def main():
    print("Hello pipeline! Checking for raw videos...\n")

    config_path = Path(__file__).resolve().parent.parent / "configs" / "config.yaml"
    if not config_path.exists():
        print(f"Couldn't find config.yaml at {config_path}.")
        return

    with open(config_path) as f:
        config = yaml.safe_load(f)

    project_root = config_path.parent.parent
    base_dir = config.get("base_dir", ".")

    # If base_dir is absolute, Path will use it directly.
    # If relative, it anchors it to project_root.
    base = (project_root / base_dir).resolve()

    search_dirs = [
        ("staging", base / Path(config.get("staging_dir", "staging")).name),
        ("input", base / Path(config.get("input_dir", "inputs")).name),
    ]

    total = 0
    for label, folder in search_dirs:
        if not folder.exists():
            print(f"  [{label}] directory '{folder}' does not exist yet.")
            continue

        videos = list(folder.rglob("*.mp4"))
        if not videos:
            print(f"  [{label}] No .mp4 files found in '{folder}'.")
            continue

        print(f"  [{label}] Found {len(videos)} video(s) in '{folder}':")
        for v in videos:
            size_mb = v.stat().st_size / (1024 * 1024)
            print(f"    - {v.name} ({size_mb:.1f} MB)")
        total += len(videos)

    if total == 0:
        print("\nNo videos found in any configured directory.")
    else:
        print(f"\nTotal: {total} video(s) discovered.")


if __name__ == "__main__":
    main()
