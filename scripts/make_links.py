#!/usr/bin/env python3
import json
import os
import random
import sys
import urllib.request

BOT_NAME = "link-dropper"
UPSTREAM = "seattleschools/media"
BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{UPSTREAM}/{BRANCH}"
MAX_LINKS = 24000

REPO_ROOT = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINKS_FILE = os.path.join(REPO_ROOT, "batch", "links.txt")

# Get the git tree of batch/ in one API call (recursive listing, no clone needed)
url = f"https://api.github.com/repos/{UPSTREAM}/git/trees/{BRANCH}?recursive=1"
headers = {
    "User-Agent": BOT_NAME,   # GitHub API requires a User-Agent; identifies the bot
    "Accept": "application/vnd.github+json",
}
if os.environ.get("GITHUB_TOKEN"):
    headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        tree = json.load(resp)["tree"]
except Exception as e:
    print(f"Failed to list upstream tree: {e}")
    sys.exit(1)

# Top-level folders under batch/
folders = sorted({
    p["path"].split("/")[1]
    for p in tree
    if p["type"] == "blob" and p["path"].startswith("batch/") and "/" in p["path"][6:]
})

if not folders:
    print("No files found under batch/ upstream.")
    sys.exit(1)

chosen = random.choice(folders)
print(f"Chosen folder: {chosen} (from {len(folders)} folders)")

prefix = f"batch/{chosen}/"
urls = [
    f"{RAW_BASE}/{p['path']}"
    for p in tree
    if p["type"] == "blob" and p["path"].startswith(prefix)
]

urls = urls[:MAX_LINKS]

os.makedirs(os.path.dirname(LINKS_FILE), exist_ok=True)
with open(LINKS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(urls))

print(f"Wrote {len(urls)} links (cap {MAX_LINKS})")
