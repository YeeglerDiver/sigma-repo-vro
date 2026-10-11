#!/usr/bin/env python3
import json
import os
import random
import string
import sys
import datetime
import urllib.request
import urllib.parse
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
MAX_PER_REPO = 16000  # Max files per individual GitHub repository (dynamically adjusted if file is large)
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
TYPE_FILE = os.path.join(REPO_ROOT, "type.txt")
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

# Determine allowed asset extensions from type.txt (Default: both .svg and .html)
allowed_exts = (".svg", ".html")
if os.path.isfile(TYPE_FILE):
    try:
        with open(TYPE_FILE, "r", encoding="utf-8") as f_type:
            type_content = f_type.read().strip().lower()
            if "svg" in type_content and "html" not in type_content:
                allowed_exts = (".svg",)
                print("Loaded filter from type.txt: Restricting search to .svg files only.")
            elif "html" in type_content and "svg" not in type_content:
                allowed_exts = (".html",)
                print("Loaded filter from type.txt: Restricting search to .html files only.")
    except Exception as e:
        print(f"Warning: Could not parse type.txt, allowing both .svg and .html: {e}")

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

# 2. Fetch upstream tree and pick a random asset matching allowed_exts from the root
tree_url = f"https://api.github.com/repos/{UPSTREAM}/git/trees/{UPSTREAM_BRANCH}?recursive=1"
req_tree = urllib.request.Request(tree_url, headers={"User-Agent": BOT_NAME, "Accept": "application/vnd.github+json"})
try:
    with urllib.request.urlopen(req_tree, timeout=60) as resp:
        tree = json.load(resp)["tree"]
except Exception as e:
    print(f"Failed to list upstream tree: {e}")
    sys.exit(1)

upstream_assets = [
    p for p in tree 
    if p["type"] == "blob" 
    and p["path"].lower().endswith(allowed_exts)
    and (not UPSTREAM_FOLDER or p["path"].startswith(UPSTREAM_FOLDER))
]

if not upstream_assets:
    print(f"No matching files found in upstream repository '{UPSTREAM}' with filter '{allowed_exts}'.")
    sys.exit(1)

# Exclude the last used template if other choices exist
filtered_assets = upstream_assets
if last_template:
    temp_filtered = [p for p in upstream_assets if p["path"] != last_template]
    if temp_filtered:
        filtered_assets = temp_filtered
        print(f"Successfully filtered out previous template '{last_template}' to ensure variety.")

random.shuffle(filtered_assets)
chosen_asset = random.choice(filtered_assets)
print(f"Chosen template for this run: {chosen_asset['path']}")

# Determine file extension (.svg or .html)
file_ext = os.path.splitext(chosen_asset["path"])[1].lower()

# Properly encode spaces and special characters for the URL download
encoded_asset_path = urllib.parse.quote(chosen_asset["path"])
raw_download_url = f"{RAW_UPSTREAM_BASE}/{encoded_asset_path}"

try:
    req_file = urllib.request.Request(raw_download_url, headers={"User-Agent": BOT_NAME})
    with urllib.request.urlopen(req_file, timeout=30) as file_resp:
        asset_content = file_resp.read()
except Exception as e:
    print(f"Failed to download template asset: {e}")
    sys.exit(1)

# Safety check: Prevent disk full error (Errno 28) for large HTML templates
file_size_bytes = len(asset_content)
max_safe_bytes_per_repo = 8 * 1024 * 1024 * 1024  # Limit to ~8GB per repo max to fit runner disk
if file_size_bytes > 0:
    calculated_max = math.floor(max_safe_bytes_per_repo / file_size_bytes)
    if calculated_max < MAX_PER_REPO:
        MAX_PER_REPO = max(100, calculated_max)
        print(f"Notice: Template file is large ({file_size_bytes / 1024:.1f} KB). Automatically adjusting max files per repo to {MAX_PER_REPO:,} to prevent disk overflow.")

# 3. Multi-Repo Chunking Loop with Disk Cleanup & Smart Hosting Selection
num_repos = math.ceil(TOTAL_LINKS / MAX_PER_REPO)
print(f"Total links requested: {TOTAL_LINKS:,} ({file_ext}). Splitting across {num_repos} repository/repositories.")

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
    
    chunk_links = []
    
    for _ in range(chunk_size):
        rand_hash = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
        filename = f"{rand_hash}{file_ext}"
        local_file_path = os.path.join(repo_batch_dir, filename)
        
        with open(local_file_path, "wb") as f_out:
            f_out.write(asset_content)
            
        # Build the correct link based on whether it's HTML (GitHub Pages) or SVG (jsDelivr CDN)
        if file_ext == ".html":
            cdn_link = f"https://{GH_USER}.github.io/{repo_name}/batch/mass_drop_{repo_idx}/{filename}"
        else:
            cdn_link = f"https://cdn.jsdelivr.net/gh/{GH_USER}/{repo_name}@main/batch/mass_drop_{repo_idx}/{filename}"
            
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
        
    # NOW that the main branch exists, enable GitHub Pages workflow source successfully!
    if file_ext == ".html":
        pages_url = f"https://api.github.com/repos/{GH_USER}/{repo_name}/pages"
        pages_payload = json.dumps({"build_type": "workflow", "source": {"branch": "main", "path": "/"}}).encode("utf-8")
        pages_req = urllib.request.Request(pages_url, data=pages_payload, headers=headers, method="POST")
        try:
            urllib.request.urlopen(pages_req)
            print(f"Enabled GitHub Pages workflow source for {repo_name}")
        except urllib.error.HTTPError as e:
            print(f"Note: Could not auto-enable Pages: {e.read().decode()}")

    # Immediately wipe local chunk files to free up runner disk space
    shutil.rmtree(repo_batch_dir, ignore_errors=True)
    print(f"Cleaned up local files for {repo_name}.")
        
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
    "template_path": chosen_asset["path"],
    "total_links": len(all_links),
    "first_link": all_links[0] if all_links else ""
}
with open(META_JSON, "w", encoding="utf-8") as f_meta:
    json.dump(metadata, f_meta, indent=2)

# Save current state so the next run knows which template was just used
os.makedirs(os.path.dirname(STATE_JSON), exist_ok=True)
state_content = {"last_template": chosen_asset["path"]}
with open(STATE_JSON, "w", encoding="utf-8") as f_state:
    json.dump(state_content, f_state, indent=2)

os.chdir(REPO_ROOT)
print("Saving state back to main control repository...")
subprocess.run(["git", "init"], check=False)
subprocess.run(["git", "config", "user.name", "link-dropper"], check=True)
subprocess.run(["git", "config", "user.email", "link-dropper@users.noreply.github.com"], check=True)
subprocess.run(["git", "add", "batch/state.json"], check=True)
subprocess.run(["git", "commit", "-m", f"Update state: last template {chosen_asset['path']}"], check=False)
control_remote = f"https://x-access-token:{GH_PAT}@github.com/{GH_USER}/sigma-repo-vro.git"
subprocess.run(["git", "push", control_remote, "HEAD:main"], check=False)

print(f"\nSuccessfully generated {len(all_links):,} total links across {len(created_repos)} repositories!")
