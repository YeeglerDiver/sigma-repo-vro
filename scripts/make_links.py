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
import math
import shutil

BOT_NAME = "link-dropper"
UPSTREAM = "donoEla/daily-linkdrops"
UPSTREAM_BRANCH = "main"

# ==========================================
# FOLDER CONFIGURATION & LIMITS
# ==========================================
UPSTREAM_FOLDER = ""  # Root directory of the upstream repo
MAX_PER_REPO = 16000  # Max files per individual GitHub repository
# ==========================================

RAW_UPSTREAM_BASE = f"https://raw.githubusercontent.com/{UPSTREAM}/{UPSTREAM_BRANCH}"
GH_USER = "YeeglerDiver"

GH_PAT = os.environ.get("GH_PAT")
if not GH_PAT:
    print("Error: GH_PAT secret is required.")
    sys.exit(1)

REPO_ROOT = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINKS_FILE = os.path.join(REPO_ROOT, "batch", "links.txt")
PREFIX_FILE = os.path.join(REPO_ROOT, "repo_prefix.txt")
AMOUNT_FILE = os.path.join(REPO_ROOT, "amount.txt")
META_JSON = os.path.join(REPO_ROOT, "batch", ".metadata.json")
STATE_JSON = os.path.join(REPO_ROOT, "batch", "state.json")

# Determine total links to generate (Default: 16000, or read from amount.txt)
TOTAL_LINKS = 16000
if os.path.isfile(AMOUNT_FILE):
    try:
        with open(AMOUNT_FILE, "r", encoding="utf-8") as f_amt:
            amt_content = f_amt.read().strip()
            digits_only = "".join(filter(str.isdigit, amt_content))
            if digits_only:
                TOTAL_LINKS = int(digits_only)
                print(f"Loaded custom link amount from amount.txt: {TOTAL_LINKS:,}")
    except Exception as e:
        print(f"Warning: Could not parse amount.txt, defaulting to {TOTAL_LINKS:,}: {e}")

# 1. Load previous run state to avoid repeating the same template file
last_template = None
if os.path.isfile(STATE_JSON):
    try:
        with open(STATE_JSON, "r", encoding="utf-8") as f_state:
            state_data = json.load(f_state)
            last_template = state_data.get("last_template")
            print(f"Loaded previous state: Last used template was '{last_template}'")
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

# 2. Fetch upstream tree and pick a random SVG file from the root
tree_url = f"https://api.github.com/repos/{UPSTREAM}/git/trees/{UPSTREAM_BRANCH}?recursive=1"
req_tree = urllib.request.Request(tree_url, headers={"User-Agent": BOT_NAME, "Accept": "application/vnd.github+json"})
try:
    with urllib.request.urlopen(req_tree, timeout=60) as resp:
        tree = json.load(resp)["tree"]
except Exception as e:
    print(f"Failed to list upstream tree: {e}")
    sys.exit(1)

upstream_svgs = [
    p for p in tree 
    if p["type"] == "blob" 
    and p["path"].lower().endswith(".svg")
    and (not UPSTREAM_FOLDER or p["path"].startswith(UPSTREAM_FOLDER))
]

if not upstream_svgs:
    print(f"No SVG files found in upstream repository '{UPSTREAM}'.")
    sys.exit(1)

# Exclude the last used template if other choices exist
filtered_svgs = upstream_svgs
if last_template:
    temp_filtered = [p for p in upstream_svgs if p["path"] != last_template]
    if temp_filtered:
        filtered_svgs = temp_filtered
        print(f"Successfully filtered out previous template '{last_template}' to ensure variety.")

random.shuffle(filtered_svgs)
chosen_svg = random.choice(filtered_svgs)
print(f"Chosen template for this run: {chosen_svg['path']}")

raw_download_url = f"{RAW_UPSTREAM_BASE}/{chosen_svg['path']}"
try:
    req_file = urllib.request.Request(raw_download_url, headers={"User-Agent": BOT_NAME})
    with urllib.request.urlopen(req_file, timeout=30) as file_resp:
        svg_content = file_resp.read()
except Exception as e:
    print(f"Failed to download template SVG: {e}")
    sys.exit(1)

# 3. Multi-Repo Chunking Loop with Disk Cleanup
num_repos = math.ceil(TOTAL_LINKS / MAX_PER_REPO)
print(f"Total links requested: {TOTAL_LINKS:,}. Splitting across {num_repos} repository/repositories.")

all_links = []
created_repos = []
remaining_links = TOTAL_LINKS

for repo_idx in range(1, num_repos + 1):
    chunk_size = min(MAX_PER_REPO, remaining_links)
    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    repo_name = f"{custom_prefix}-{date_str}-{time_slot}-{repo_idx}-{rand_suffix}"
    
    print(f"\n--- Processing Repo {repo_idx}/{num_repos}: {repo_name} ({chunk_size:,} files) ---")
    
    # Create repo via API
    api_url = "https://api.github.com/user/repos"
    payload = json.dumps({"name": repo_name, "private": False, "auto_init": False}).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {GH_PAT}",
        "Accept": "application/vnd.github+json",
        "User-Agent": BOT_NAME,
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Successfully created repository: {repo_name}")
    except urllib.error.HTTPError as e:
        print(f"Failed to create repo {repo_name}: {e.code} - {e.read().decode()}")
        sys.exit(1)
        
    # Generate files for this repo chunk
    repo_batch_dir = os.path.join(REPO_ROOT, "batch", f"mass_drop_{repo_idx}")
    os.makedirs(repo_batch_dir, exist_ok=True)
    
    cdn_base = f"https://cdn.jsdelivr.net/gh/{GH_USER}/{repo_name}@main"
    chunk_links = []
    
    for _ in range(chunk_size):
        rand_hash = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
        filename = f"{rand_hash}.svg"
        local_file_path = os.path.join(repo_batch_dir, filename)
        
        with open(local_file_path, "wb") as f_out:
            f_out.write(svg_content)
            
        cdn_link = f"{cdn_base}/batch/{os.path.basename(repo_batch_dir)}/{filename}"
        chunk_links.append(cdn_link)
        all_links.append(cdn_link)
        
    # Git commit and push chunk
    os.chdir(REPO_ROOT)
    subprocess.run(["rm", "-rf", ".git"], check=False)
    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "branch", "-M", "main"], check=True)
    subprocess.run(["git", "config", "user.name", "link-dropper"], check=True)
    subprocess.run(["git", "config", "user.email", "link-dropper@users.noreply.github.com"], check=True)
    subprocess.run(["git", "config", "http.postBuffer", "524288000"], check=True)
    
    subprocess.run(["git", "add", f"batch/mass_drop_{repo_idx}/"], check=True)
    subprocess.run(["git", "commit", "-m", f"Mass drop chunk {repo_idx} ({chunk_size} files)"], check=True)
    
    remote_url = f"https://x-access-token:{GH_PAT}@github.com/{GH_USER}/{repo_name}.git"
    subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
    
    push_result = subprocess.run(["git", "push", "-u", "origin", "main", "--force"])
    if push_result.returncode != 0:
        print(f"Error: Git push failed for {repo_name}!")
        sys.exit(1)
        
    # Immediately wipe local chunk files to free up runner disk space & inodes
    shutil.rmtree(repo_batch_dir, ignore_errors=True)
    print(f"Cleaned up local files for {repo_name} to free disk space.")
        
    created_repos.append(repo_name)
    remaining_links -= chunk_size

# Write all compiled links to links.txt
os.makedirs(os.path.dirname(LINKS_FILE), exist_ok=True)
with open(LINKS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(all_links) + "\n")

# Save run metadata for Discord notification
metadata = {
    "repo_name": created_repos[0] if created_repos else "unknown",
    "repos_created": created_repos,
    "template_path": chosen_svg["path"],
    "total_links": len(all_links),
    "first_link": all_links[0] if all_links else ""
}
with open(META_JSON, "w", encoding="utf-8") as f_meta:
    json.dump(metadata, f_meta, indent=2)

# Save current state so the next run knows which template was just used
os.makedirs(os.path.dirname(STATE_JSON), exist_ok=True)
state_content = {"last_template": chosen_svg["path"]}
with open(STATE_JSON, "w", encoding="utf-8") as f_state:
    json.dump(state_content, f_state, indent=2)

os.chdir(REPO_ROOT)
print("Saving state back to main control repository...")
subprocess.run(["git", "init"], check=False)
subprocess.run(["git", "config", "user.name", "link-dropper"], check=True)
subprocess.run(["git", "config", "user.email", "link-dropper@users.noreply.github.com"], check=True)
subprocess.run(["git", "add", "batch/state.json"], check=True)
subprocess.run(["git", "commit", "-m", f"Update state: last template {chosen_svg['path']}"], check=False)
control_remote = f"https://x-access-token:{GH_PAT}@github.com/{GH_USER}/sigma-repo-vro.git"
subprocess.run(["git", "push", control_remote, "HEAD:main"], check=False)

print(f"\nSuccessfully generated {len(all_links):,} total links across {len(created_repos)} repositories!")
