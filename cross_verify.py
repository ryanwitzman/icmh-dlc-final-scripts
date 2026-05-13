import os
import glob
from collections import Counter

csv_dir = "/N/project/msk_dl/icmh-dlc-final-scripts/outputs/postprocessed/batch_full_run_01"
staging_dir = "/N/project/msk_dl/icmh-dlc-final-scripts/staging"

# 1. Clean the CSV names: remove '.csv' and the '.trimmed' suffix/prefix
csv_files = glob.glob(os.path.join(csv_dir, "*.csv"))
processed_clean = set()
for f in csv_files:
    name = os.path.splitext(os.path.basename(f))[0]
    # Strip the logic used by the pipeline
    clean_name = name.replace("trimmed_", "").replace(".trimmed", "")
    processed_clean.add(clean_name)

# 2. Clean the staging names
staging_files = glob.glob(os.path.join(staging_dir, "*.*"))
staging_basenames = []
failed_videos = []

for f in staging_files:
    raw_name = os.path.splitext(os.path.basename(f))[0]
    # Clean staging name to match the logic
    clean_staging = raw_name.replace("trimmed_", "").replace(".trimmed", "")
    staging_basenames.append(clean_staging)
    
    if clean_staging not in processed_clean:
        failed_videos.append(os.path.basename(f))

# 3. Check for duplicates (Files that resolve to the same ID)
counts = Counter(staging_basenames)
duplicates = {name: count for name, count in counts.items() if count > 1}

print(f"Total files in staging: {len(staging_files)}")
print(f"Unique video IDs processed: {len(processed_clean)}\n")

if duplicates:
    print(f"--- Detected {len(duplicates)} ID collisions ---")
    print("These are cases where 'video.mp4' and 'trimmed_video.trimmed.mp4' both exist.")
    # Optional: print(duplicates) 

print(f"\n--- Actually Missing (No version processed): {len(failed_videos)} ---")
for video in sorted(failed_videos):
    print(video)