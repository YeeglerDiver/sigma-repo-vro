#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request

BOT_NAME = "link-dropper"
TOTAL_LINKS = 16000

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

boundary = "----DiscordWebhookBoundarySigmaRepoVro"
data = []

payload = {
    "content": f"🚀 **{BOT_NAME} — Full Mass CDN Drop Complete!**\n📊 Generated **{len(links)}** fresh individual links from a single template SVG.\n📁 Complete `links.txt` file attached below:"
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9"
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
