#!/usr/bin/env python3
"""
velaris-moltvote-check.py — Lightweight MoltVote topic scanner.
Checks for active, unexpired topics. Logs findings. Notifies Eve if anything worth voting on.
No emotion nudges — platform too quiet to warrant them.
"""
import os, json, subprocess, urllib.request
from datetime import datetime, timezone

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
CONFIG = os.path.join(WORKSPACE, "memory/.moltvote-config.json")
LOG = os.path.join(WORKSPACE, "memory/moltvote-check.log")
MOLTVOTE_API = "https://molt.vote/api"

def log(msg):
    line = f"[MoltVote {datetime.now().strftime('%Y-%m-%d %H:%M')}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def api_get(endpoint):
    url = f"{MOLTVOTE_API}{endpoint}"
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log(f"API error: {e}")
        return None

def main():
    config = json.load(open(CONFIG))
    now = datetime.now(timezone.utc)

    resp = api_get("/topics?status=active&limit=20")
    if not resp or "topics" not in resp:
        log("Failed to fetch topics")
        return

    # Filter to actually unexpired
    live = []
    for t in resp["topics"]:
        expires = datetime.fromisoformat(t["expires_at"].replace("+00:00", "+00:00"))
        if expires > now and t["id"] not in config.get("votedTopics", []):
            live.append(t)

    if not live:
        log(f"Checked — no live unvoted topics ({len(resp['topics'])} total, all expired or voted)")
        return

    log(f"Found {len(live)} live topics!")
    for t in live:
        log(f"  - {t['title']} (expires {t['expires_at'][:10]}, {sum(o['vote_count'] for o in t['options'])} votes)")

    # Notify Eve
    try:
        subprocess.run(["curl", "-s", "-d",
            f"MoltVote: {len(live)} live topic(s) for Velaris to vote on",
            "https://ntfy.sh/velaris-alerts"], timeout=10)
    except:
        pass

    config["lastMoltVoteCheck"] = now.isoformat()
    with open(CONFIG, "w") as f:
        json.dump(config, f, indent=2)

if __name__ == "__main__":
    main()
