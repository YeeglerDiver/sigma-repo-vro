#!/usr/bin/env python3
import os
import random

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_BASE = "https://raw.githubusercontent.com/seattleschools/media/main"
BATCH_DIR = os.path.join(REPO_ROOT, "batch")
LINKS_FILE = os.path.join(REPO_ROOT, "batch", "links.txt")
MAX_LINKS = 24000

# 1. List all subfolders under batch/
folders = [d for d in os.listdir(BATCH_DIR)
           if os.path.isdir(os.path.join(BATCH_DIR, d))
           and not d.startswith((".", "_"))]   # skip hidden/meta dirs like ".git"

if not folders:
    raise SystemExit("No folders found in batch/")

# 2. Pick one at random
chosen = random.choice(folders)
print(f"Chosen folder: {chosen}")

# 3. Walk it and collect file links
urls = []
for root, dirs, files in os.walk(os.path.join(BATCH_DIR, chosen)):
    for fname in files:
        if fname.startswith("."):
            continue
        rel = os.path.relpath(os.path.join(root, fname), REPO_ROOT)
        urls.append(f"{RAW_BASE}/{rel.replace(os.sep, '/')}")

urls = urls[:MAX_LINKS]

with open(LINKS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(urls))

print(f"Wrote {len(urls)} links from {chosen} (cap {MAX_LINKS})")
