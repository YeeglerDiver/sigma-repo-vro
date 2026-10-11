#!/usr/bin/env python3
import json
import os
import random
import string
import sys
import datetime
import urllib.request
import subprocess
import re

BOT_NAME = "link-dropper"
UPSTREAM = "seattleschools/media"
UPSTREAM_BRANCH = "main"

# ==========================================
# FOLDER CONFIGURATION
# ==========================================
UPSTREAM_FOLDER = "batch/" 
# ==========================================

RAW_UPSTREAM_BASE = f"https://raw.githubusercontent.com/{UPSTREAM}/{UPSTREAM_BRANCH}"
TOTAL_LINKS = 16000
GH_USER = "YeeglerDiver"

GH_PAT = os.environ.get("GH_PAT")
if not GH_PAT:
    print("Error: GH_PAT secret is required.")
    sys.exit(1)

REPO_ROOT = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_BATCH_DIR = os.path.join(REPO_ROOT, "batch", "mass_drop")
LINKS_FILE = os.path.join(REPO_ROOT, "batch", "links.txt")
PREFIX_FILE = os.path.join(REPO_ROOT, "repo_prefix.txt")
META_JSON = os.path.join(REPO_ROOT, "batch", ".metadata.json")
STATE_JSON = os.path.join(REPO_ROOT, "batch", "state.json")

# 1. Load previous run state to avoid repeating the same directory
last_dir = None
if os.path.isfile(STATE_JSON):
    try:
        with open(STATE_JSON, "r", encoding="utf-8") as f_state:
            state_data = json.load(f_state)
            last_dir = state_data.get("last_dir")
            print(f"Loaded previous state: Last used directory was '{last_dir}'")
    except Exception as e:
        print(f"Warning: Could not read state.json: {e}")

# Read words from repo_prefix.txt and randomly pick at least 3 words
custom_prefix = "sigma-assets"
if os.path.isfile(PREFIX_FILE):
    with open(PREFIX_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        raw_words = re.findall(r'[a-zA-Z0-9]+', content)
        words = [w.lower() for w in raw_words if w]
        
        if words:
            num_to_pick = random.randint(3, len(words)) if len(words) >= 3 else len(words)
            chosen_words = random.sample(words, num_to_pick)
            custom_prefix = "-".join(chosen_words)

# Determine time slot (morning, midday, afternoon) based on current UTC hour
now_utc = datetime.datetime.now(datetime.timezone.utc)
hour = now_utc.hour
if hour < 11:
    time_slot = "morning"
elif hour < 16:
    time_slot = "midday"
else:
    time_slot = "afternoon"

date_str = now_utc.strftime("%Y%m%d")
rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
NEW_REPO_NAME = f"{custom_prefix}-{date_str}-{time_slot}-{rand_suffix}"

print(f"Targeting new unique repository: {NEW_REPO_NAME} (slot: {time_slot})")

# 2. Create the unique repository on GitHub via API
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

# 3. Fetch upstream tree and pick a random SVG file (excluding the last used directory)
tree_url = f"https://api.github.com/repos/{UPSTREAM}/git/trees/{UPSTREAM_BRANCH}?recursive=1"
req_tree = urllib.request.Request(tree_url, headers={"User-Agent": BOT_NAME, "Accept": "application/vnd.github+json"})
try:
    with urllib.request.urlopen(req_tree, timeout=60) as resp:
        tree = json.load(resp)["tree"]
except Exception as e:
    print(f"Failed to list upstream tree: {e}")
    sys.exit(1)

# Filter valid SVGs in batch/
upstream_svgs = [
    p for p in tree 
    if p["type"] == "blob" 
    and p["path"].lower().endswith(".svg")
    and p["path"].startswith(UPSTREAM_FOLDER)
]

if not upstream_svgs:
    print(f"No SVG files found in upstream folder '{UPSTREAM_FOLDER}'.")
    sys.exit(1)

# Helper function to extract the immediate subdirectory name under batch/
def get_parent_dir(path):
    parts = path.split("/")
    if len(parts) > 2:
        return parts[0] + "/" + parts[1] # e.g., "batch/FolderName"
    return path

# Exclude the last used directory if other choices exist
filtered_svgs = upstream_svgs
if last_dir:
    temp_filtered = [p for p in upstream_svgs if get_parent_dir(p["path"]) != last_dir]
    if temp_filtered:
        filtered_svgs = temp_filtered
        print(f"Successfully filtered out previous directory '{last_dir}' to ensure variety.")
    else:
        print("Notice: Only one directory available in upstream, ignoring filter to prevent deadlock.")

random.shuffle(filtered_svgs)
chosen_svg = random.choice(filtered_svgs)
chosen_dir = get_parent_dir(chosen_svg["path"])
print(f"Chosen template for this run: {chosen_svg['path']} (Directory: {chosen_dir})")

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

print(f"Generating {TOTAL_LINKS} physical files using template: {chosen_svg['path']}...")
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

# Save run metadata for Discord notification
metadata = {
    "repo_name": NEW_REPO_NAME,
    "template_path": chosen_svg["path"],
    "total_links": len(new_links),
    "first_link": new_links[0] if new_links else ""
}
with open(META_JSON, "w", encoding="utf-8") as f_meta:
    json.dump(metadata, f_meta, indent=2)

# Save current state so the next run knows which directory was just used
os.makedirs(os.path.dirname(STATE_JSON), exist_ok=True)
state_content = {"last_dir": chosen_dir, "last_template": chosen_svg["path"]}
with open(STATE_JSON, "w", encoding="utf-8") as f_state:
    json.dump(state_content, f_state, indent=2)

# 4. Save state back to the MAIN control repo FIRST so it persists for the next schedule
os.chdir(REPO_ROOT)
print("Saving state back to main control repository...")
subprocess.run(["git", "config", "user.name", "link-dropper"], check=True)
subprocess.run(["git", "config", "user.email", "link-dropper@users.noreply.github.com"], check=True)
subprocess.run(["git", "add", "batch/state.json"], check=True)
subprocess.run(["git", "commit", "-m", f"Update state: last dir {chosen_dir}"], check=False)
control_remote = f"https://x-access-token:{GH_PAT}@github.com/{GH_USER}/sigma-repo-vro.git" # Replace with your control repo name if different
subprocess.run(["git", "push", control_remote, "HEAD:main"], check=False)

print(f"Generated {len(new_links)} links. Pushing to new dynamic repository {NEW_REPO_NAME}...")

# 5. Switch git remote to the NEW dynamic repository and push the 16k files
subprocess.run(["rm", "-rf", ".git"], check=False)
subprocess.run(["git", "init"], check=True)
subprocess.run(["git", "branch", "-M", "main"], check=True)
subprocess.run(["git", "config", "user.name", "link-dropper"], check=True)
subprocess.run(["git", "config", "user.email", "link-dropper@users.noreply.github.com"], check=True)

subprocess.run(["git", "add", "batch/mass_drop/", "batch/links.txt", "batch/.metadata.json"], check=True)
subprocess.run(["git", "commit", "-m", f"Mass generate 16k links from {chosen_svg['path']}"], check=True)

remote_url = f"https://x-access-token:{GH_PAT}@github.com/{GH_USER}/{NEW_REPO_NAME}.git"
subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)

push_result = subprocess.run(["git", "push", -u, "origin", "main", "--force"])
if push_result.returncode != 0:
    print("Error: Git push to dynamic repo failed!")
    sys.exit(1)

print("Successfully pushed all files and updated state!")
