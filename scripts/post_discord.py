#!/usr/bin/env python3
import os
import urllib.request
import json

webhook = os.environ.get("WEBHOOK")
if not webhook:
    print("No webhook set, skipping.")
    raise SystemExit(0)

links_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "batch", "links.txt")
with open(links_file) as f:
    links = [l for l in f.read().splitlines() if l.strip()]

newest = links[-10:]
payload = json.dumps({"content": f"**Daily CDN drop** — {len(links)}/24000 links total\n" + "\n".join(newest)}).encode()
req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"})
urllib.request.urlopen(req)
