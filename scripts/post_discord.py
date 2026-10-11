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
template_path = "unknown"
total_links = 16000
first_link = ""

if os.path.isfile(meta_file):
    try:
        with open(meta_file, "r", encoding="utf-8") as f_meta:
            meta = json.load(f_meta)
            repo_name = meta.get("repo_name", repo_name)
            template_path = meta.get("template_path", template_path)
            total_links = meta.get("total_links", total_links)
            first_link = meta.get("first_link", first_link)
    except Exception as e:
        print(f"Warning: Failed to load metadata: {e}")

repo_url = f"https://github.com/{GH_USER}/{repo_name}"
jsdelivr_url = f"https://cdn.jsdelivr.net/gh/{GH_USER}/{repo_name}@main/batch/mass_drop/"
current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

boundary = "----DiscordWebhookBoundaryInteractiveDrop"
data = []

# Build a rich, interactive Discord Embed
embed = {
    "title": "🚀 Mass CDN Drop Successfully Deployed!",
    "description": f"A brand new dynamic repository has been created, populated with **{total_links:,}** cloned assets, and pushed live via jsDelivr.",
    "color": 0x2ecc71,  # Emerald Green
    "fields": [
        {
            "name": "📁 Target Repository",
            "value": f"[`{repo_name}`]({repo_url})",
            "inline": True
        },
        {
            "name": "📊 Total Generated Links",
            "value": f"`{total_links:,} files`",
            "inline": True
        },
        {
            "name": "🎨 Upstream Template Used",
            "value": f"`{template_path}`",
            "inline": False
        },
        {
            "name": "🔗 Quick Action Links",
            "value": f"• [📦 Open GitHub Repository]({repo_url})\n• [🧪 Test First Link in Browser]({first_link})\n• [⚡ Root jsDelivr CDN Endpoint]({jsdelivr_url})",
            "inline": False
        }
    ],
    "footer": {
        "text": f"Bot: {BOT_NAME} • Deployed at {current_time}"
    }
}

payload = {
    "content": "🔔 **New Batch Drop Alert!** Check out the live links below:",
    "embeds": [embed]
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
