#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error

GH_USER = "YeeglerDiver"
CONTROL_REPO = "sigma-repo-vro"  # Safety check: NEVER delete your main control repo!

GH_PAT = os.environ.get("GH_PAT")
if not GH_PAT:
    print("Error: GH_PAT secret is required.")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {GH_PAT}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "repo-cleaner"
}

print("Scanning for empty repositories...")
page = 1
empty_repos = []

while True:
    url = f"https://api.github.com/user/repos?per_page=100&page={page}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            repos = json.load(resp)
    except Exception as e:
        print(f"Failed to fetch repos: {e}")
        break
        
    if not repos:
        break
        
    for repo in repos:
        name = repo["name"]
        
        # Never touch the main control repo
        if name == CONTROL_REPO:
            continue
            
        # Check if the repository has any branches (meaning it's completely empty / uninitialized)
        branches_url = f"https://api.github.com/repos/{GH_USER}/{name}/branches"
        b_req = urllib.request.Request(branches_url, headers=headers)
        try:
            with urllib.request.urlopen(b_req) as b_resp:
                branches = json.load(b_resp)
                if len(branches) == 0:
                    empty_repos.append(name)
        except urllib.error.HTTPError as e:
            # If the repo is brand new and has zero commits, listing branches can throw an error or return empty
            if e.code in (404, 409):
                empty_repos.append(name)
        except Exception:
            pass
            
    page += 1

if not empty_repos:
    print("No empty repositories found. All clean!")
    sys.exit(0)

print(f"Found {len(empty_repos)} empty repository/ies: {empty_repos}")

# Delete the empty repositories
for repo_name in empty_repos:
    del_url = f"https://api.github.com/repos/{GH_USER}/{repo_name}"
    del_req = urllib.request.Request(del_url, headers=headers, method="DELETE")
    try:
        with urllib.request.urlopen(del_req) as resp:
            print(f"Successfully deleted empty repository: {repo_name}")
    except urllib.error.HTTPError as e:
        print(f"Failed to delete {repo_name} ({e.code}): {e.read().decode()}")

print("Cleanup complete!")
