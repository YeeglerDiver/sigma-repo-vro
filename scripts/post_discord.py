#!/usr/bin/env python3
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

BOT_NAME = "link-dropper"[cite: 19]
GH_USER = "YeeglerDiver"[cite: 19]

webhook = os.environ.get("WEBHOOK")[cite: 19]
if not webhook:
    print("No webhook set, skipping.")[cite: 19]
    sys.exit(0)[cite: 19]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))[cite: 19]
links_file = os.path.join(REPO_ROOT, "batch", "links.txt")[cite: 19]
meta_file = os.path.join(REPO_ROOT, "batch", ".metadata.json")[cite: 19]

if not os.path.isfile(links_file):
    print(f"links.txt not found at {links_file}")[cite: 19]
    sys.exit(1)[cite: 19]

with open(links_file, "r", encoding="utf-8") as f:
    links = [l.strip() for l in f.read().splitlines() if l.strip()][cite: 19]

if not links:
    print("links.txt is empty, nothing to post.")[cite: 19]
    sys.exit(0)[cite: 19]

meta = {}[cite: 19]
if os.path.isfile(meta_file):
    try:
        with open(meta_file, "r", encoding="utf-8") as fm:
            meta = json.load(fm)[cite: 19]
            print(f"Successfully loaded metadata: {meta}")[cite: 19]
    except Exception as e:
        print(f"Warning: Could not parse .metadata.json: {e}")[cite: 19]

first_link = (meta.get("first_link") or links[0]).strip()[cite: 19]
repo_name = (meta.get("repo_name") or f"{GH_USER}-drop").strip()[cite: 19]

is_html = ".github.io" in first_link[cite: 19]
asset_type = "HTML (Live GitHub Pages)" if is_html else "SVG (jsDelivr CDN)"[cite: 19]
hosting_badge = "🌐 Live Interactive Site" if is_html else "⚡ Fast CDN Delivery"[cite: 19]

now_utc = datetime.datetime.now(datetime.timezone.utc)[cite: 19]
unix_time = int(now_utc.timestamp())[cite: 19]

event_name = os.environ.get("GITHUB_EVENT_NAME", "unknown")[cite: 19]

if event_name == "workflow_dispatch":
    trigger_desc = "👤 **Manual Run** (Triggered via Actions tab)"[cite: 19]
else:
    hour = now_utc.hour[cite: 19]
    run_slot = (hour // 3) + 1[cite: 19]
    if run_slot > 8:
        run_slot = 8[cite: 19]
    trigger_desc = f"⏰ **Scheduled Run** (Daily Run #{run_slot} of 8)"[cite: 19]

repo_url = f"https://github.com/{GH_USER}/{repo_name}".strip()[cite: 19]
raw_links_url = f"https://raw.githubusercontent.com/{GH_USER}/{repo_name}/main/links.txt".strip()[cite: 19]

print(f"Test First Link URL: {first_link}")[cite: 19]
print(f"GitHub Repo URL: {repo_url}")[cite: 19]
print(f"Raw links.txt URL: {raw_links_url}")[cite: 19]

def send_discord_file(file_bytes: bytes, filename: str, content: str = "", embed: dict = None):
    boundary = "----DiscordWebhookBoundarySigmaRepoVro"[cite: 19]
    data = []

    payload_json = {}
    if content:
        payload_json["content"] = content
    if embed:
        payload_json["embeds"] = [embed]

    data.append(f"--{boundary}\r\n".encode("utf-8"))[cite: 19]
    data.append(b"Content-Disposition: form-data; name=\"payload_json\"\r\n")[cite: 19]
    data.append(b"Content-Type: application/json\r\n\r\n")[cite: 19]
    data.append(json.dumps(payload_json).encode("utf-8") + b"\r\n")[cite: 19]

    data.append(f"--{boundary}\r\n".encode("utf-8"))[cite: 19]
    data.append(f"Content-Disposition: form-data; name=\"files[0]\"; filename=\"{filename}\"\r\n".encode("utf-8"))
    data.append(b"Content-Type: text/plain; charset=utf-8\r\n\r\n")[cite: 19]
    data.append(file_bytes + b"\r\n")[cite: 19]
    data.append(f"--{boundary}--\r\n".encode("utf-8"))[cite: 19]

    body = b"".join(data)[cite: 19]
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",[cite: 19]
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"[cite: 19]
    }

    req = urllib.request.Request(webhook, data=body, headers=headers)[cite: 19]
    try:
        resp = urllib.request.urlopen(req, timeout=45)[cite: 19]
        print(f"Sent {filename} successfully ({resp.status}).")
    except urllib.error.HTTPError as e:
        print(f"Discord webhook error {e.code}: {e.read().decode(errors='replace')}")[cite: 19]
        sys.exit(1)[cite: 19]
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}")[cite: 19]
        sys.exit(1)[cite: 19]

# Split the full links list into chunks safely under 20 MB each
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
    "title": "🚀 Mass Asset Drop Deployment Complete",[cite: 19]
    "description": (
        "A fresh batch of individual links has been successfully generated, distributed across dynamic repositories, and deployed.\n\n"[cite: 19]
        "🔗 **Quick Access Links:**\n"[cite: 19]
        f"• **[Test First Link]({first_link})**\n"[cite: 19]
        f"• **[View GitHub Repo]({repo_url})**\n"[cite: 19]
        f"• **[Raw links.txt]({raw_links_url})**"[cite: 19]
    ),
    "color": 5793266,[cite: 19]
    "fields": [
        {
            "name": "⚙️ Execution Type",[cite: 19]
            "value": trigger_desc,[cite: 19]
            "inline": False[cite: 19]
        },
        {
            "name": "🕒 Completion Time",[cite: 19]
            "value": f"<t:{unix_time}:F> (<t:{unix_time}:R>)",[cite: 19]
            "inline": False[cite: 19]
        },
        {
            "name": "📊 Total Links Generated",[cite: 19]
            "value": f"`{len(links):,}` files",[cite: 19]
            "inline": True[cite: 19]
        },
        {
            "name": "📁 Asset Format",[cite: 19]
            "value": f"`{asset_type}`",[cite: 19]
            "inline": True[cite: 19]
        },
        {
            "name": "🔗 Hosting Status",[cite: 19]
            "value": hosting_badge,[cite: 19]
            "inline": False[cite: 19]
        }
    ],
    "footer": {
        "text": f"{BOT_NAME} • Automated Multi-Repo System (1/{total_parts})"
    },
    "timestamp": now_utc.isoformat()[cite: 19]
}

# Upload each chunk
for idx, chunk in enumerate(chunks, start=1):
    chunk_bytes = ("\n".join(chunk) + "\n").encode("utf-8")
    part_filename = "links.txt" if total_parts == 1 else f"links_part_{idx}_of_{total_parts}.txt"

    if idx == 1:
        # First file includes the main notification ping and full embed
        send_discord_file(
            file_bytes=chunk_bytes,
            filename=part_filename,
            content="@here",[cite: 19]
            embed=main_embed
        )
    else:
        # Brief pause between sequential uploads to avoid hitting Discord rate limits
        time.sleep(2)
        send_discord_file(
            file_bytes=chunk_bytes,
            filename=part_filename,
            content=f"📦 **Attachment Part {idx} of {total_parts}** (`{len(chunk):,}` links)"
        )

print("All link attachments posted to Discord successfully!")
