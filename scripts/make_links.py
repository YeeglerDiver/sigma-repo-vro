#!/usr/bin/env python3
import os
import random
import sys

REPO_ROOT = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATCH_DIR = os.path.join(REPO_ROOT, "batch")
LINKS_FILE = os.path.join(BATCH_DIR, "links.txt")
MAX_LINKS = 24000

if not os.path.isdir(BATCH_DIR):
    print(f"batch/ not found at {BATCH_DIR}")
    print(f"Repo root contents: {os.listdir(REPO_ROOT)}")
    sys.exit(1)

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
