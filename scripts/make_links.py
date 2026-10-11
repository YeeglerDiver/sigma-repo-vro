#!/usr/bin/env python3
import datetime
import os
import random
import string
import sys

BOT_NAME = "link-dropper"
MAX_LINKS = 24000
BATCH_SIZE = 30  # How many fresh links to create each day

REPO_ROOT = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINKS_FILE = os.path.join(REPO_ROOT, "batch", "links.txt")

# Load existing links
existing_links = []
if os.path.isfile(LINKS_FILE):
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        existing_links = [line.strip() for line in f if line.strip()]

if len(existing_links) >= MAX_LINKS:
    print(f"Reached max limit of {MAX_LINKS} links. Nothing to create.")
    sys.exit(0)

# Generate a batch of brand-new, unique links using random strings and timestamps
today_str = datetime.datetime.utcnow().strftime("%Y%m%d")
new_batch = []

for _ in range(BATCH_SIZE):
    # Create a unique random hash/string for this new link
    random_hash = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    
    # Construct a custom unique CDN link based on your repo
    # (jsDelivr serves files from your repo: cdn.jsdelivr.net/gh/USERNAME/REPO@main/path/file)
    unique_link = f"https://cdn.jsdelivr.net/gh/YeeglerDiver/sigma-repo-vro@main/batch/generated/{today_str}_{random_hash}.txt"
    
    if unique_link not in existing_links:
        new_batch.append(unique_link)

# Combine existing links with the new batch up to the cap
updated_links = (existing_links + new_batch)[:MAX_LINKS]

os.makedirs(os.path.dirname(LINKS_FILE), exist_ok=True)
with open(LINKS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(updated_links) + "\n")

print(f"Created {len(new_batch)} fresh links today. Total: {len(updated_links)}/{MAX_LINKS}")
