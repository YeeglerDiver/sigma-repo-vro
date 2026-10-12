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

UPSTREAM_FOLDER = ""
MAX_PER_REPO = 16000

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
FILE_WORDS_FILE = os.path.join(REPO_ROOT, "file_words.txt")
META_JSON = os.path.join(REPO_ROOT, "batch", ".metadata.json")
STATE_JSON = os.path.join(REPO_ROOT, "batch", "state.json")

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

allowed_exts = (".svg", ".html")
if os.path.isfile(TYPE_FILE):
    try:
        with open(TYPE_FILE, "r", encoding="utf-8") as f_type:
            type_content = f_type.read().strip().lower()
            if "svg" in type_content and "html" not in type_content:
                allowed_exts = (".svg",)
            elif "html" in type_content and "svg" not in type_content:
                allowed_exts = (".html",)
    except Exception as e:
        print(f"Warning: Could not parse type.txt: {e}")

asset_word_pool = []
if os.path.isfile(FILE_WORDS_FILE):
    try:
        with open(FILE_WORDS_FILE, "r", encoding="utf-8") as f_fw:
            asset_word_pool = [w.strip().lower() for w in re.findall(r'[a-zA-Z0-9]+', f_fw.read()) if w.strip()]
            print(f"Loaded {len(asset_word_pool)} words from file_words.txt for asset naming.")
    except Exception as e:
        print(f"Warning: Could not parse file_words.txt: {e}")

last_template = None
if os.path.isfile(STATE_JSON):
    try:
        with open(STATE_JSON, "r", encoding="utf-8") as f_state:
            state_data = json.load(f_state)
            last_template = state_data.get("last_template")
    except Exception as e:
        print(f"Warning: Could not read state.json: {e}")

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

now_utc = datetime.datetime.now(datetime.timezone.utc)
date_str = now_utc.strftime("%Y%m%d")

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
    print(f"No matching files found in upstream repository '{UPSTREAM}'.")
    sys.exit(1)

filtered_assets = upstream_assets
if last_template:
    temp_filtered = [p for p in upstream_assets if p["path"] != last_template]
    if temp_filtered:
        filtered_assets = temp_filtered

random.shuffle(filtered_assets)
chosen_asset = random.choice(filtered_assets)
print(f"Chosen template for this run: {chosen_asset['path']}")

file_ext = os.path.splitext(chosen_asset["path"])[1].lower()

if file_ext == ".html" and TOTAL_LINKS > 6000:
    TOTAL_LINKS = 6000

encoded_asset_path = urllib.parse.quote(chosen_asset["path"])
raw_download_url = f"{RAW_UPSTREAM_BASE}/{encoded_asset_path}"

try:
    req_file = urllib.request.Request(raw_download_url, headers={"User-Agent": BOT_NAME})
    with urllib.request.urlopen(req_file, timeout=30) as file_resp:
        asset_content = file_resp.read()
except Exception as e:
    print(f"Failed to download template asset: {e}")
    sys.exit(1)

num_repos = math.ceil(TOTAL_LINKS / MAX_PER_REPO)
print(f"Total links requested: {TOTAL_LINKS:,} ({file_ext}). Splitting across {num_repos} repository/repositories.")

all_links = []
created_repos = []
remaining_links = TOTAL_LINKS

for repo_idx in range(1, num_repos + 1):
    chunk_size = min(MAX_PER_REPO, remaining_links)
    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    repo_name = f"{custom_prefix}-{date_str}-{rand_suffix}"
    
    print(f"\n--- Processing Repo {repo_idx}/{num_repos}: {repo_name} ({chunk_size:,} files) ---")
    
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
        
    repo_batch_dir = os.path.join(REPO_ROOT, "batch", f"root_drop_{repo_idx}")
    os.makedirs(repo_batch_dir, exist_ok=True)
    
    chunk_links = []
    
    for _ in range(chunk_size):
        if asset_word_pool and len(asset_word_pool) >= 2:
            chosen_words = random.sample(asset_word_pool, min(2, len(asset_word_pool)))
            file_rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            filename = f"{'-'.join(chosen_words)}-{file_rand_suffix}{file_ext}"
        elif asset_word_pool:
            file_rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            filename = f"{random.choice(asset_word_pool)}-{file_rand_suffix}{file_ext}"
        else:
            rand_hash = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
            filename = f"{rand_hash}{file_ext}"

        local_file_path = os.path.join(repo_batch_dir, filename)
        with open(local_file_path, "wb") as f_out:
            f_out.write(asset_content)
            
        if file_ext == ".html":
            file_endpoints = [
                f"https://{GH_USER}.github.io/{repo_name}/{filename}"
            ]
        else:
            file_endpoints = [
                f"https://cdn.jsdelivr.net/gh/{GH_USER}/{repo_name}@main/{filename}",
                f"https://fastly.jsdelivr.net/gh/{GH_USER}/{repo_name}@main/{filename}",
                f"https://gcore.jsdelivr.net/gh/{GH_USER}/{repo_name}@main/{filename}",
                f"https://testingcf.jsdelivr.net/gh/{GH_USER}/{repo_name}@main/{filename}",
                f"https://cdn.staticaly.com/gh/{GH_USER}/{repo_name}/main/{filename}",
                f"https://raw.githack.com/{GH_USER}/{repo_name}/main/{filename}",
                f"https://rawcdn.githack.com/{GH_USER}/{repo_name}/main/{filename}",
                f"https://raw.githubusercontent.com/{GH_USER}/{repo_name}/main/{filename}",
                f"https://esm.sh/gh/{GH_USER}/{repo_name}@main/{filename}",
                f"https://raw.esm.sh/gh/{GH_USER}/{repo_name}@main/{filename}",
                f"https://ghproxy.net/https://raw.githubusercontent.com/{GH_USER}/{repo_name}/main/{filename}",
                f"https://mirror.ghproxy.com/https://raw.githubusercontent.com/{GH_USER}/{repo_name}/main/{filename}",
                f"https://raw.kkgithub.com/{GH_USER}/{repo_name}/main/{filename}",
                f"https://raw.staticdn.net/{GH_USER}/{repo_name}/main/{filename}",
                f"https://raw.gitmirror.com/{GH_USER}/{repo_name}/main/{filename}"
            ]
            
        chunk_links.extend(file_endpoints)
        all_links.extend(file_endpoints)

    os.chdir(REPO_ROOT)
    subprocess.run(["rm", "-rf", ".git"], check=False)
    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "branch", "-M", "main"], check=True)
    subprocess.run(["git", "config", "user.name", "link-dropper"], check=True)
    subprocess.run(["git", "config", "user.email", "link-dropper@users.noreply.github.com"], check=True)
    subprocess.run(["git", "config", "http.postBuffer", "524288000"], check=True)
    
    for f_name in os.listdir(repo_batch_dir):
        shutil.move(os.path.join(repo_batch_dir, f_name), os.path.join(REPO_ROOT, f_name))
    
    if repo_idx == 1:
        os.makedirs(os.path.dirname(LINKS_FILE), exist_ok=True)
        with open(LINKS_FILE, "w", encoding="utf-8") as f_links:
            f_links.write("\n".join(chunk_links) + "\n")
        shutil.copy(LINKS_FILE, os.path.join(REPO_ROOT, "links.txt"))

    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-m", f"Mass drop root chunk {repo_idx} ({chunk_size} files)"], check=True)
    
    remote_url = f"https://x-access-token:{GH_PAT}@github.com/{GH_USER}/{repo_name}.git"
    subprocess.run(["git", "remote", "add", "origin", remote_url], check=True)
    
    push_result = subprocess.run("git push -u origin main --force", shell=True)
    if push_result.returncode != 0:
        print(f"Error: Git push failed for {repo_name}!")
        sys.exit(1)
        
    if file_ext == ".html":
        pages_url = f"https://api.github.com/repos/{GH_USER}/{repo_name}/pages"
        pages_payload = json.dumps({"source": {"branch": "main", "path": "/"}}).encode("utf-8")
        pages_req = urllib.request.Request(pages_url, data=pages_payload, headers=headers, method="POST")
        try:
            urllib.request.urlopen(pages_req)
        except urllib.error.HTTPError as e:
            print(f"Note: Could not auto-enable Pages: {e.read().decode()}")

    for f_name in os.listdir(REPO_ROOT):
        if f_name.endswith(file_ext) or f_name == "links.txt":
            try:
                os.remove(os.path.join(REPO_ROOT, f_name))
            except:
                pass
    shutil.rmtree(repo_batch_dir, ignore_errors=True)
    print(f"Cleaned up local files for {repo_name}.")
        
    created_repos.append(repo_name)
    remaining_links -= chunk_size

os.makedirs(os.path.dirname(LINKS_FILE), exist_ok=True)
with open(LINKS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(all_links) + "\n")

metadata = {
    "repo_name": created_repos[0] if created_repos else "unknown",
    "repos_created": created_repos,
    "template_path": chosen_asset["path"],
    "total_links": len(all_links),
    "first_link": all_links[0] if all_links else ""
}
with open(META_JSON, "w", encoding="utf-8") as f_meta:
    json.dump(metadata, f_meta, indent=2)

os.makedirs(os.path.dirname(STATE_JSON), exist_ok=True)
state_content = {"last_template": chosen_asset["path"]}
with open(STATE_JSON, "w", encoding="utf-8") as f_state:
    json.dump(state_content, f_state, indent=2)

os.chdir(REPO_ROOT)
subprocess.run(["git", "init"], check=False)
subprocess.run(["git", "config", "user.name", "link-dropper"], check=True)
subprocess.run(["git", "config", "user.email", "link-dropper@users.noreply.github.com"], check=True)
subprocess.run(["git", "add", "batch/state.json", "batch/.metadata.json"], check=True)
subprocess.run(["git", "commit", "-m", f"Update state and batch metadata for drop ({len(all_links)} links)"], check=False)
control_remote = f"https://x-access-token:{GH_PAT}@github.com/{GH_USER}/sigma-repo-vro.git"
subprocess.run(["git", "push", control_remote, "HEAD:main"], check=False)

print(f"\nSuccessfully generated {len(all_links):,} total links across {len(created_repos)} repositories!")
