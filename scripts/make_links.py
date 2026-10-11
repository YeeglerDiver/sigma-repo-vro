#!/usr/bin/env python3
import json
import os
import sys
import urllib.request

BOT_NAME = "link-dropper"
UPSTREAM = "seattleschools/media"
UPSTREAM_BRANCH = "main"
RAW_UPSTREAM_BASE = f"https://raw.githubusercontent.com/{UPSTREAM}/{UPSTREAM_BRANCH}"
MAX_LINKS = 24000
BATCH_SIZE = 30  # Number of SVGs to download and add per run

CHOSEN_FOLDER = "smokingonzaandcoke"

REPO_ROOT = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_BATCH_DIR = os.path.join(REPO_ROOT, "batch", CHOSEN_FOLDER)
LINKS_FILE = os.path.join(REPO_ROOT, "batch", "links.txt")

# 1. Fetch upstream file list via GitHub API
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

prefix = f"batch/{CHOSEN_FOLDER}/"
# Filter specifically for SVG files
upstream_files = [
    p for p in tree
    if p["type"] == "blob" and p["path"].startswith(prefix) and p["path"].lower().endswith(".svg")
]

if not upstream_files:
    print(f"No SVG files found under {prefix} upstream.")
    sys.exit(1)

# Load existing links to check what's already been added
existing_links = []
if os.path.isfile(LINKS_FILE):
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        existing_links = [line.strip() for line in f if line.strip()]

if len(existing_links) >= MAX_LINKS:
    print(f"Reached max limit of {MAX_LINKS} links. Nothing to do.")
    sys.exit(0)

os.makedirs(LOCAL_BATCH_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LINKS_FILE), exist_ok=True)

downloaded_count = 0
new_links = []

for item in upstream_files:
    if len(existing_links) + len(new_links) >= MAX_LINKS:
        break
        
    file_path_in_tree = item["path"]
    filename = os.path.basename(file_path_in_tree)
    local_file_path = os.path.join(LOCAL_BATCH_DIR, filename)
    
    # Construct official jsDelivr CDN link pointing to YOUR repository
    my_cdn_link = f"https://cdn.jsdelivr.net/gh/YeeglerDiver/sigma-repo-vro@main/batch/{CHOSEN_FOLDER}/{filename}"
    
    if my_cdn_link in existing_links:
        continue
        
    # Download the SVG file content from upstream
    raw_download_url = f"{RAW_UPSTREAM_BASE}/{file_path_in_tree}"
    try:
        req_file = urllib.request.Request(raw_download_url, headers={"User-Agent": BOT_NAME})
        with urllib.request.urlopen(req_file, timeout=30) as file_resp:
            file_content = file_resp.read()
            
        # Save it locally into your repository
        with open(local_file_path, "wb") as f_out:
            f_out.write(file_content)
            
        new_links.append(my_cdn_link)
        downloaded_count += 1
        print(f"Downloaded and saved: {filename}")
        
        if downloaded_count >= BATCH_SIZE:
            break
    except Exception as e:
        print(f"Error downloading {filename}: {e}")

if not new_links:
    print("No new SVG files to download.")
    sys.exit(0)

# Combine existing + new links up to MAX_LINKS
updated_links = (existing_links + new_links)[:MAX_LINKS]

with open(LINKS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(updated_links) + "\n")

print(f"Added {len(new_links)} new jsDelivr links. Total links: {len(updated_links)}/{MAX_LINKS}")
