"""
cleanup_old_jobs.py

A utility script to delete old job folders under /usr/src/app/output/ 
AND /usr/src/app/user_configs/ if they exceed a certain age.

Usage:
  - Run manually with 'python cleanup_old_jobs.py'
  - Or schedule via crontab or a background worker.

Adjust OUTPUT_DIRS and MAX_AGE_HOURS as you like.
"""

import os
import time
import shutil

# If you need to clean both output and user_configs:
OUTPUT_DIRS     = [
    "/usr/src/app/output",
    "/usr/src/app/user_configs"
]

MAX_AGE_HOURS   = .2  # Delete any job folder older than 1 hour

def cleanup_old_results():
    now = time.time()

    for base_dir in OUTPUT_DIRS:
        if not os.path.isdir(base_dir):
            print(f"[WARN] Directory not found: {base_dir}")
            continue

        for item_name in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item_name)
            # We only delete if it's a directory (likely a job folder named by UUID).
            if os.path.isdir(item_path):
                mtime = os.path.getmtime(item_path)
                age_hours = (now - mtime) / 3600.0
                if age_hours > MAX_AGE_HOURS:
                    print(f"[CLEANUP] Deleting old job folder: {item_path} (age={age_hours:.1f} hrs)")
                    shutil.rmtree(item_path, ignore_errors=True)


if __name__ == "__main__":
    cleanup_old_results()
