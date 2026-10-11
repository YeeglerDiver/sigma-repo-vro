#!/usr/bin/env python3
import json
import os
import random
import string
import sys
import datetime
import urllib.request
import subprocess

BOT_NAME = "link-dropper"
UPSTREAM = "seattleschools/media"
UPSTREAM_BRANCH = "main"
RAW_UPSTREAM_BASE = f"https://raw.githubusercontent.com/{UPSTREAM}/{UPSTREAM_BRANCH}"
TOTAL_LINKS = 16000
GH_USER = "YeeglerDiver"

GH_PAT = os.environ.get("GH_PAT")
if not GH_PAT:
    print("Error: GH_PAT secret is required to create a new repository.")
    sys.exit(1)

REPO_ROOT = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_BATCH_DIR = os.path.join(REPO_ROOT, "batch", "mass_drop")
LINKS_FILE = os.path.join(REPO_ROOT, "batch", "links.txt")

# Generate a unique repo name every run (timezone-aware UTC)
timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M")
rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
NEW_REPO_NAME = f"sigma-assets-{timestamp}-{rand_suffix}"

print(f"Targeting new unique repository: {NEW_REPO_NAME}")

# 1. Create the unique repository on GitHub via API
api_url = "https://api.github.com/user/repos"
payload = json.dumps({
    "name": NEW_REPO_NAME,
    "private": False,
    "auto_init": False
}).encode("utf-8")

headers = {
    "Authorization": f"Bearer {GH_PAT}",
    "Accept": "application/vnd.github+json",
    "User-Agent": BOT_NAME,
    "Content-Type": "application/json"
}

req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")
try:
    with urllib.request.urlopen(req) as resp:
        print(f"Successfully created new repository: {NEW_REPO_NAME}")
except urllib.error.HTTPError as e:
    print(f"Failed to create repo via API ({e.code}): {e.read().decode()}")
    sys.exit(1)

# 2. Fetch upstream template SVG
tree_url = f"https://api.github.com/repos/{UPSTREAM}/git/trees/{UPSTREAM_BRANCH}?recursive=1"
req_tree = urllib.request.Request(tree_url, headers={"User-Agent": BOT_NAME, "Accept": "application/vnd.github+json"})
try:
    with urllib.request.urlopen(req_tree, timeout=60) as resp:
        tree = json.load(resp)["tree"]
except Exception as e:
    print(f"Failed to list upstream tree: {e}")
    sys.exit(1)

upstream_svgs = [p for p in tree if p["type"] == "blob" and p["path"].lower().endswith(".svg")]
if not upstream_svgs:
    print("No SVG files found upstream.")
    sys.exit(1)

chosen_svg = random.choice(upstream_svgs)
raw_download_url = f"{RAW_UPSTREAM_BASE}/{chosen_svg['path']}"

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
CDN_BASE = f"https://cdn.jsdelivr.net/gh/{GH_USER}/{NEW_REPO_NAME}@main"

print(f"Generating {TOTAL_LINKS} physical files...")
for _ in range(TOTAL_LINKS):
    rand_hash = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    filename = f"{rand_hash}.svg"
    local_file_path = os.path.join(LOCAL_BATCH_DIR, filename)
    
    with open(local_file_path, "wb") as f_out:
        f_out.write(svg_content)
        
    cdn_link = f"{CDN_BASE}/batch/mass_drop/{filename}"
    new_links.append(cdn_link)

with open(LINKS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(new_links) + "\n")

print(f"Generated {len(new_links)} links pointing to {NEW_REPO_NAME}. Pushing to GitHub...")

# 3. Git commit and push directly via Python subprocess
os.chdir(REPO_ROOT)
subprocess.run(["rm", "-rf", ".git"], check=False)
subprocess.run(["git", "init"], check=True)
subprocess.run(["git", "branch", "-M", "main"], check=True)
subprocess.run(["git", "config", "user.name", "link-dropper"], check=True)
subprocess.run(["git", "config", "user.email", "link-dropper@users.noreply.github.com"], check=True)
subprocess.run(["git", "add", "batch/"], check=True)
subprocess.run(["git", "commit", "-m", "Mass generate 16k fresh CDN links"], check=True)

remote_url = f"https://x-access-token:{GH_PAT}@github.com/{GH_USER}/{NEW_REPO_NAME}.git"
subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
subprocess.run(["git", "push", "-u", "origin", "main", "--force"], check=True)

print("Successfully pushed all files to the new unique repository!")
