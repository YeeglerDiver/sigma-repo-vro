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

newest = links[-24000:]
content = f"**{BOT_NAME} — Daily CDN drop** — {len(links)}/{MAX_LINKS} links total\n" + "\n".join(newest)

# Discord hard-caps message content at 2000 chars
if len(content) > 2000:
    content = content[:1997] + "..."

payload = json.dumps({"content": content}).encode()

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
