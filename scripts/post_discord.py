#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request
import datetime

BOT_NAME = "link-dropper"
GH_USER = "YeeglerDiver"

webhook = os.environ.get("WEBHOOK")
if not webhook:
    print("No webhook set, skipping.")
    sys.exit(0)

batch_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "batch")
links_file = os.path.join(batch_dir, "links.txt")
meta_file = os.path.join(batch_dir, ".metadata.json")

if not os.path.isfile(links_file):
    print(f"links.txt not found at {links_file}")
    sys.exit(1)

# Load metadata if available
repo_name = "unknown-repo"
template_path = "unknown.svg"
total_links = 16000

if os.path.isfile(meta_file):
    try:
        with open(meta_file, "r", encoding="utf-8") as f_meta:
            meta = json.load(f_meta)
            repo_name = meta.get("repo_name", repo_name)
            template_path = meta.get("template_path", template_path)
            total_links = meta.get("total_links", total_links)
    except Exception as e:
        print(f"Warning: Failed to load metadata: {e}")

# Read first 5 links from links.txt for preview
first_links = []
with open(links_file, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i < 5:
            first_links.append(f"{i+1}. {line.strip()}")
        else:
            break

repo_url = f"https://github.com/{GH_USER}/{repo_name}"
raw_github_url = f"https://raw.githubusercontent.com/{GH_USER}/{repo_name}/main/batch/links.txt"
jsdelivr_url = f"https://cdn.jsdelivr.net/gh/{GH_USER}/{repo_name}@main/batch/links.txt"
first_link_url = first_links[0].split(". ", 1)[1] if first_links else repo_url

current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")

boundary = "----DiscordWebhookBoundaryInteractiveDrop"
data = []

# Build the rich embed mimicking your requested layout
embed = {
    "title": f"✨ Batch Drop: {total_links:,} Links Generated!",
    "description": f"Successfully compiled and deployed dynamic batch assets into repository **`{repo_name}`**.",
    "color": 0x5865F2,  # Discord Blurple
    "fields": [
        {
            "name": "GitHub Account",
            "value": f"`{GH_USER}`",
            "inline": True
        },
        {
            "name": "Total Links",
            "value": f"`{total_links:,} links`",
            "inline": True
        },
        {
            "name": "Provider",
            "value": "`jsDelivr / Fastly`",
            "inline": True
        },
        {
            "name": "Main Site File",
            "value": f"`{os.path.basename(template_path)}`",
            "inline": True
        },
        {
            "name": "Repositories Created",
            "value": f"- [`{repo_name}`]({repo_url})",
            "inline": False
        },
        {
            "name": "Link Preview (First 5)",
            "value": "\n".join(first_links) if first_links else "No links found.",
            "inline": False
        }
    ],
    "footer": {
        "text": f"Requested by {GH_USER} • Discord CDN LinkGen • {current_time}"
    }
}

# Interactive Action Buttons (with external link arrows)
components = [
    {
        "type": 1,  # Action Row
        "components": [
            {
                "type": 2,  # Button
                "style": 5,  # Link Button (opens URL in browser)
                "label": "Open GitHub Repo",
                "url": repo_url
            },
            {
                "type": 2,
                "style": 5,
                "label": "Test 1st CDN Link",
                "url": first_link_url
            },
            {
                "type": 2,
                "style": 5,
                "label": "View Raw Links",
                "url": raw_github_url
            }
        ]
    }
]

payload = {
    "content": "📦 **New Automated Drop Ready!** Direct files and interactive options below:",
    "embeds": [embed],
    "components": components
}

data.append(f"--{boundary}\r\n".encode("utf-8"))
data.append(b"Content-Disposition: form-data; name=\"payload_json\"\r\n")
data.append(b"Content-Type: application/json\r\n\r\n")
data.append(json.dumps(payload).encode("utf-8") + b"\r\n")

with open(links_file, "rb") as f:
    file_bytes = f.read()

data.append(f"--{boundary}\r\n".encode("utf-8"))
data.append(b"Content-Disposition: form-data; name=\"files[0]\"; filename=\"links.txt\"\r\n")
data.append(b"Content-Type: text/plain; charset=utf-8\r\n\r\n")
data.append(file_bytes + b"\r\n")

data.append(f"--{boundary}--\r\n".encode("utf-8"))
body = b"".join(data)

headers = {
    "Content-Type": f"multipart/form-data; boundary={boundary}",
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

req = urllib.request.Request(webhook, data=body, headers=headers)
try:
    resp = urllib.request.urlopen(req, timeout=30)
    print(f"Discord responded with status {resp.status}")
except urllib.error.HTTPError as e:
    print(f"Discord webhook error {e.code}: {e.read().decode(errors='replace')}")
    sys.exit(1)
except urllib.error.URLError as e:
    print(f"Network error: {e.reason}")
    sys.exit(1)
