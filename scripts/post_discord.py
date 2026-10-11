#!/usr/bin/env python3
import json
import os
import sys
import datetime
import urllib.error
import urllib.request

BOT_NAME = "link-dropper"

webhook = os.environ.get("WEBHOOK")
if not webhook:
    print("No webhook set, skipping.")
    sys.exit(0)

links_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "batch", "links.txt")
if not os.path.isfile(links_file):
    print(f"links.txt not found at {links_file}")
    sys.exit(1)

with open(links_file, "r", encoding="utf-8") as f:
    links = [l for l in f.read().splitlines() if l.strip()]

if not links:
    print("links.txt is empty, nothing to post.")
    sys.exit(0)

# Detect if the drop was HTML (GitHub Pages) or SVG (jsDelivr CDN) based on the first link
is_html = ".github.io" in links[0]
asset_type = "HTML (Live GitHub Pages)" if is_html else "SVG (jsDelivr CDN)"
hosting_badge = "🌐 Live Interactive Site" if is_html else "⚡ Fast CDN Delivery"

# Get current UTC time for the embed timestamp
now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

boundary = "----DiscordWebhookBoundarySigmaRepoVro"
data = []

# Rich Embed Payload design
payload = {
    "content": "@here",  # Triggers the notification ping cleanly
    "embeds": [
        {
            "title": "🚀 Mass Asset Drop Deployment Complete",
            "description": "A fresh batch of individual links has been successfully generated, distributed across dynamic repositories, and deployed.",
            "color": 5793266,  # Vibrant Cyan/Blue Accent
            "fields": [
                {
                    "name": "📊 Total Links Generated",
                    "value": f"`{len(links):,}` files",
                    "inline": True
                },
                {
                    "name": "⚙️ Asset Format",
                    "value": f"`{asset_type}`",
                    "inline": True
                },
                {
                    "name": "🔗 Hosting Status",
                    "value": hosting_badge,
                    "inline": False
                },
                {
                    "name": "📥 Attached File",
                    "value": "The complete list of generated links (`links.txt`) is attached below for easy access.",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"{BOT_NAME} • Automated Multi-Repo System"
            },
            "timestamp": now_utc
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
