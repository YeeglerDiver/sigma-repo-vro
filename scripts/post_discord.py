#!/usr/bin/env python3
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

BOT_NAME = "link-dropper"
GH_USER = "YeeglerDiver"
CONTROL_REPO = "sigma-repo-vro"

webhook = os.environ.get("WEBHOOK")
if not webhook:
    print("No webhook set, skipping.")
    sys.exit(0)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
links_file = os.path.join(REPO_ROOT, "batch", "links.txt")
meta_file = os.path.join(REPO_ROOT, "batch", ".metadata.json")

if not os.path.isfile(links_file):
    print(f"links.txt not found at {links_file}")
    sys.exit(1)

with open(links_file, "r", encoding="utf-8") as f:
    links = [l for l in f.read().splitlines() if l.strip()]

if not links:
    print("links.txt is empty, nothing to post.")
    sys.exit(0)

# Load metadata if available for repo name and first link
meta = {}
if os.path.isfile(meta_file):
    try:
        with open(meta_file, "r", encoding="utf-8") as fm:
            meta = json.load(fm)
    except Exception:
        pass

first_link = meta.get("first_link") or links[0]
repo_name = meta.get("repo_name") or f"{GH_USER}-drop"

# Detect if the drop was HTML (GitHub Pages) or SVG (jsDelivr CDN)
is_html = ".github.io" in first_link
asset_type = "HTML (Live GitHub Pages)" if is_html else "SVG (jsDelivr CDN)"
hosting_badge = "🌐 Live Interactive Site" if is_html else "⚡ Fast CDN Delivery"

# Get current time and Unix timestamp for Discord's dynamic local formatting
now_utc = datetime.datetime.now(datetime.timezone.utc)
unix_time = int(now_utc.timestamp())

event_name = os.environ.get("GITHUB_EVENT_NAME", "unknown")

if event_name == "workflow_dispatch":
    trigger_desc = "👤 **Manual Run** (Triggered via Actions tab)"
else:
    hour = now_utc.hour
    run_slot = (hour // 3) + 1
    if run_slot > 8:
        run_slot = 8
    trigger_desc = f"⏰ **Scheduled Run** (Daily Run #{run_slot} of 8)"

boundary = "----DiscordWebhookBoundarySigmaRepoVro"
data = []

# URLs for Discord buttons
repo_url = f"https://github.com/{GH_USER}/{repo_name}"
raw_links_url = f"https://raw.githubusercontent.com/{GH_USER}/{CONTROL_REPO}/main/batch/links.txt"

# Rich Embed Payload design with Discord Buttons (Components) & Dynamic Local Time
payload = {
    "content": "@here",  # Triggers notification ping
    "embeds": [
        {
            "title": "🚀 Mass Asset Drop Deployment Complete",
            "description": "A fresh batch of individual links has been successfully generated, distributed across dynamic repositories, and deployed.",
            "color": 5793266,  # Vibrant Cyan/Blue Accent
            "fields": [
                {
                    "name": "⚙️ Execution Type",
                    "value": trigger_desc,
                    "inline": False
                },
                {
                    "name": "🕒 Completion Time",
                    "value": f"<t:{unix_time}:F> (<t:{unix_time}:R>)",
                    "inline": False
                },
                {
                    "name": "📊 Total Links Generated",
                    "value": f"`{len(links):,}` files",
                    "inline": True
                },
                {
                    "name": "📁 Asset Format",
                    "value": f"`{asset_type}`",
                    "inline": True
                },
                {
                    "name": "🔗 Hosting Status",
                    "value": hosting_badge,
                    "inline": False
                }
            ],
            "footer": {
                "text": f"{BOT_NAME} • Automated Multi-Repo System"
            },
            "timestamp": now_utc.isoformat()
        }
    ],
    "components": [
        {
            "type": 1,  # Action Row
            "components": [
                {
                    "type": 2,  # Button
                    "style": 5,  # Link button style
                    "label": "Test First Link",
                    "url": first_link
                },
                {
                    "type": 2,
                    "style": 5,
                    "label": "View GitHub Repo",
                    "url": repo_url
                },
                {
                    "type": 2,
                    "style": 5,
                    "label": "Raw links.txt",
                    "url": raw_links_url
                }
            ]
        }
    ]
}

# Construct multipart/form-data payload for Discord webhook with file attachment
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
