#!/usr/bin/env python3
import json
import os
import sys
import urllib.request

BOT_NAME = "link-dropper"
UPSTREAM = "seattleschools/media"
BRANCH = "main"
RAW_BASE = f"https://cdn.jsdelivr.net/gh/{UPSTREAM}@{BRANCH}"
MAX_LINKS = 24000

# Locked to your chosen folder so it repeats the same one every time
CHOSEN_FOLDER = "smokingonzaandcoke"

REPO_ROOT = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINKS_FILE = os.path.join(REPO_ROOT, "batch", "links.txt")

# Get the git tree of batch/ in one API call (recursive listing, no clone needed)
url = f"https://api.github.com/repos/{UPSTREAM}/git/trees/{BRANCH}?recursive=1"
headers = {
    "User-Agent": BOT_NAME,    # GitHub API requires a User-Agent; identifies the bot
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

prefix = f"batch/{CHOSEN_FOLDER}/"
urls = [
    f"{RAW_BASE}/{p['path']}"
    for p in tree
    if p["type"] == "blob" and p["path"].startswith(prefix)
]

if not urls:
    print(f"No files found under {prefix} upstream.")
    sys.exit(1)

urls = urls[:MAX_LINKS]

os.makedirs(os.path.dirname(LINKS_FILE), exist_ok=True)
with open(LINKS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(urls))

print(f"Chosen folder: {CHOSEN_FOLDER} (locked)")
print(f"Wrote {len(urls)} links (cap {MAX_LINKS})")
