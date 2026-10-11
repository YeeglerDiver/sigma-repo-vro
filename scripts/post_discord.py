#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request

BOT_NAME = "link-dropper"
MAX_LINKS = 24000

webhook = os.environ.get("WEBHOOK")
if not webhook:
    print("No webhook set, skipping.")
    sys.exit(0)

links_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "batch", "links.txt")
if not os.path.isfile(links_file):
    print(f"links.txt not found at {links_file}")
    sys.exit(1)

with open(links_file) as f:
    links = [l for l in f.read().splitlines() if l.strip()]

if not links:
    print("links.txt is empty, nothing to post.")
    sys.exit(0)

total_links = len(links)
percentage = min(100.0, (total_links / MAX_LINKS) * 100)

# Generate a clean visual progress bar
bar_length = 10
filled_length = int(bar_length * total_links // MAX_LINKS)
bar = "█" * filled_length + "░" * (bar_length - filled_length)

# Grab the latest 5 links for a clean code-block display
recent_links = links[-5:]
recent_links_text = "\n".join(recent_links)

# Build a professional Discord Embed payload
embed = {
    "title": "🚀 Daily CDN Link Drop",
    "color": 5763719,  # Vibrant green accent
    "fields": [
        {
            "name": "📊 Progress & Status",
            "value": f"`{bar}` **{total_links}** / **{MAX_LINKS}** links ({percentage:.1f}%)",
            "inline": False
        },
        {
            "name": "🔗 Latest Added Links",
            "value": f"```text\n{recent_links_text}\n```",
            "inline": False
        }
    ],
    "footer": {
        "text": f"{BOT_NAME} • Automated GitHub Sync"
    }
}

payload = json.dumps({"embeds": [embed]}).encode()

# Include a full browser User-Agent to bypass Cloudflare's bot check (Error 1010)
headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9"
}

req = urllib.request.Request(webhook, data=payload, headers=headers)
try:
    resp = urllib.request.urlopen(req, timeout=30)
    print(f"Discord responded with status {resp.status}")
except urllib.error.HTTPError as e:
    print(f"Discord webhook error {e.code}: {e.read().decode(errors='replace')}")
    sys.exit(1)
except urllib.error.URLError as e:
    print(f"Network error: {e.reason}")
    sys.exit(1)
