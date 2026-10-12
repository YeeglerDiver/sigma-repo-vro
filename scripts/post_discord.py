#!/usr/bin/env python3
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

BOT_NAME = "link-dropper"
GH_USER = "YeeglerDiver"

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
    links = [l.strip() for l in f.read().splitlines() if l.strip()]

if not links:
    print("links.txt is empty, nothing to post.")
    sys.exit(0)

meta = {}
if os.path.isfile(meta_file):
    try:
        with open(meta_file, "r", encoding="utf-8") as fm:
            meta = json.load(fm)
            print(f"Successfully loaded metadata: {meta}")
    except Exception as e:
        print(f"Warning: Could not parse .metadata.json: {e}")

first_link = (meta.get("first_link") or links[0]).strip()
repo_name = (meta.get("repo_name") or f"{GH_USER}-drop").strip()

is_html = ".github.io" in first_link
asset_type = "HTML (Live GitHub Pages)" if is_html else "SVG (jsDelivr CDN)"
hosting_badge = "🌐 Live Interactive Site" if is_html else "⚡ Fast CDN Delivery"

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

repo_url = f"https://github.com/{GH_USER}/{repo_name}".strip()
raw_links_url = f"https://raw.githubusercontent.com/{GH_USER}/{repo_name}/main/links.txt".strip()

print(f"Test First Link URL: {first_link}")
print(f"GitHub Repo URL: {repo_url}")
print(f"Raw links.txt URL: {raw_links_url}")

def send_discord_file(file_bytes: bytes, filename: str, content: str = "", embed: dict = None):
    boundary = "----DiscordWebhookBoundarySigmaRepoVro"
    data = []

    payload_json = {}
    if content:
        payload_json["content"] = content
    if embed:
        payload_json["embeds"] = [embed]

    data.append(f"--{boundary}\r\n".encode("utf-8"))
    data.append(b"Content-Disposition: form-data; name=\"payload_json\"\r\n")
    data.append(b"Content-Type: application/json\r\n\r\n")
    data.append(json.dumps(payload_json).encode("utf-8") + b"\r\n")

    data.append(f"--{boundary}\r\n".encode("utf-8"))
    data.append(f"Content-Disposition: form-data; name=\"files[0]\"; filename=\"{filename}\"\r\n".encode("utf-8"))
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
        resp = urllib.request.urlopen(req, timeout=45)
        print(f"Sent {filename} successfully ({resp.status}).")
    except urllib.error.HTTPError as e:
        print(f"Discord webhook error {e.code}: {e.read().decode(errors='replace')}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}")
        sys.exit(1)

MAX_CHUNK_BYTES = 20 * 1024 * 1024
chunks = []
current_chunk = []
current_size = 0

for line in links:
    encoded_len = len(line.encode("utf-8")) + 1
    if current_size + encoded_len > MAX_CHUNK_BYTES and current_chunk:
        chunks.append(current_chunk)
        current_chunk = [line]
        current_size = encoded_len
    else:
        current_chunk.append(line)
        current_size += encoded_len

if current_chunk:
    chunks.append(current_chunk)

total_parts = len(chunks)
print(f"Splitting {len(links):,} links across {total_parts} attachment file(s)...")

main_embed = {
    "title": "🚀 Mass Asset Drop Deployment Complete",
    "description": (
        "A fresh batch of individual links has been successfully generated, distributed across dynamic repositories, and deployed.\n\n"
        "🔗 **Quick Access Links:**\n"
        f"• **[Test First Link]({first_link})**\n"
        f"• **[View GitHub Repo]({repo_url})**\n"
        f"• **[Raw links.txt]({raw_links_url})**"
    ),
    "color": 5793266,
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
        "text": f"{BOT_NAME} • Automated Multi-Repo System (1/{total_parts})"
    },
    "timestamp": now_utc.isoformat()
}

for idx, chunk in enumerate(chunks, start=1):
    chunk_bytes = ("\n".join(chunk) + "\n").encode("utf-8")
    part_filename = "links.txt" if total_parts == 1 else f"links_part_{idx}_of_{total_parts}.txt"

    if idx == 1:
        send_discord_file(
            file_bytes=chunk_bytes,
            filename=part_filename,
            content="@here",
            embed=main_embed
        )
    else:
        time.sleep(2)
        send_discord_file(
            file_bytes=chunk_bytes,
            filename=part_filename,
            content=f"📦 **Attachment Part {idx} of {total_parts}** (`{len(chunk):,}` links)"
        )

print("All link attachments posted to Discord successfully!")
