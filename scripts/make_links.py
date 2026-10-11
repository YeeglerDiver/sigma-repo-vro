#!/usr/bin/env python3
import os
import random
import sys

REPO_ROOT = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATCH_DIR = os.path.join(REPO_ROOT, "batch")
LINKS_FILE = os.path.join(BATCH_DIR, "links.txt")
MAX_LINKS = 24000
RAW_BASE = f"https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY', 'OWNER/REPO')}/main"

if not os.path.isdir(BATCH_DIR):
    print(f"batch/ not found at {BATCH_DIR}")
    print(f"Repo root contents: {os.listdir(REPO_ROOT)}")
    sys.exit(1)

# List subfolders; fall back to walking batch/ itself if none exist
folders = sorted(
    d for d in os.listdir(BATCH_DIR)
    if os.path.isdir(os.path.join(BATCH_DIR, d))
)

if folders:
    chosen = random.choice(folders)
    walk_root = os.path.join(BATCH_DIR, chosen)
else:
    print("No subfolders in batch/ — walking batch/ directly.")
    chosen = "batch"
    walk_root = BATCH_DIR

print(f"Chosen folder: {chosen}")

urls = []
for root, dirs, files in os.walk(walk_root):
    for fname in files:
        if fname.startswith(".") or fname == "links.txt":
            continue
        rel = os.path.relpath(os.path.join(root, fname), REPO_ROOT)
        urls.append(f"{RAW_BASE}/{rel.replace(os.sep, '/')}")

urls = urls[:MAX_LINKS]

with open(LINKS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(urls))

print(f"Wrote {len(urls)} links from {chosen} (cap {MAX_LINKS})")
