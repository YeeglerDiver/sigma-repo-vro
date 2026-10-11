#!/usr/bin/env python3
import json
import os
import random
import string
import sys
import urllib.request

BOT_NAME = "link-dropper"
UPSTREAM = "seattleschools/media"
UPSTREAM_BRANCH = "main"
RAW_UPSTREAM_BASE = f"https://raw.githubusercontent.com/{UPSTREAM}/{UPSTREAM_BRANCH}"
CDN_BASE = f"https://cdn.jsdelivr.net/gh/YeeglerDiver/sigma-repo-vro@main"
TOTAL_LINKS = 16000

REPO_ROOT = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_BATCH_DIR = os.path.join(REPO_ROOT, "batch", "mass_drop")
LINKS_FILE = os.path.join(REPO_ROOT, "batch", "links.txt")

# 1. Fetch upstream file list via GitHub API (recursive)
url = f"https://api.github.com/repos/{UPSTREAM}/git/trees/{UPSTREAM_BRANCH}?recursive=1"
headers = {
    "User-Agent": BOT_NAME,
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

# Find all SVG files anywhere in the upstream repo
upstream_svgs = [
    p for p in tree
    if p["type"] == "blob" and p["path"].lower().endswith(".svg")
]

if not upstream_svgs:
    print("No SVG files found upstream.")
    sys.exit(1)

# Pick one single random SVG file to use as the template
chosen_svg = random.choice(upstream_svgs)
file_path_in_tree = chosen_svg["path"]
print(f"Chosen template SVG: {file_path_in_tree}")

# Download the content of that template SVG
raw_download_url = f"{RAW_UPSTREAM_BASE}/{file_path_in_tree}"
try:
    req_file = urllib.request.Request(raw_download_url, headers={"User-Agent": BOT_NAME})
    with urllib.request.urlopen(req_file, timeout=30) as file_resp:
        svg_content = file_resp.read()
except Exception as e:
    print(f"Failed to download template SVG: {e}")
    sys.exit(1)

os.makedirs(LOCAL_BATCH_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LINKS_FILE), exist_ok=True)

new_links = []
print(f"Generating {TOTAL_LINKS} individual physical files and links...")

# Create 16,000 unique physical copies with random hashes
for _ in range(TOTAL_LINKS):
    rand_hash = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    filename = f"{rand_hash}.svg"
    local_file_path = os.path.join(LOCAL_BATCH_DIR, filename)
    
    # Save physical copy locally
    with open(local_file_path, "wb") as f_out:
        f_out.write(svg_content)
        
    # Build unique jsDelivr CDN link
    cdn_link = f"{CDN_BASE}/batch/mass_drop/{filename}"
    new_links.append(cdn_link)

# Completely replace links.txt (no stacking)
with open(LINKS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(new_links) + "\n")

print(f"Successfully generated {len(new_links)} fresh links and replaced links.txt.")
