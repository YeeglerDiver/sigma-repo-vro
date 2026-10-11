#!/usr/bin/env python3
import os
import json

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_BASE = "https://raw.githubusercontent.com/seattleschools/media/main"
MAX_LINKS = 24000
SKIP_DIRS = {".git", ".github", "scripts"}
LINKS_FILE = os.path.join(REPO_ROOT, "batch", "links.txt")

urls = []
for root, dirs, files in os.walk(REPO_ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for fname in files:
        rel = os.path.relpath(os.path.join(root, fname), REPO_ROOT)
        urls.append(f"{RAW_BASE}/{rel.replace(os.sep, '/')}")

# newest-added folders tend to sort last; keep the cap by trimming the oldest
urls = urls[-MAX_LINKS:]

os.makedirs(os.path.dirname(LINKS_FILE), exist_ok=True)
with open(LINKS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(urls))

with open(os.path.join(REPO_ROOT, "batch", "state.json"), "w") as f:
    json.dump({"count": len(urls), "max": MAX_LINKS}, f)

print(f"Wrote {len(urls)} links (cap {MAX_LINKS})")
