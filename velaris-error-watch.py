#!/usr/bin/env python3
import os, glob, re, json, requests
from datetime import datetime

SEEN_FILE = os.path.expanduser("~/.openclaw/workspace/memory/.error-watch-seen.json")
NTFY_URL = "https://ntfy.sh/velaris-gloria-9kx"
ERROR_PATTERNS = [
    r"Error|error|ERROR",
    r"Traceback",
    r"IndentationError",
    r"SyntaxError",
    r"cannot access local variable",
    r"No such file or directory",
    r"failed|FAILED",
]

def load_seen():
    try:
        return json.load(open(SEEN_FILE))
    except:
        return {}

def save_seen(seen):
    json.dump(seen, open(SEEN_FILE, "w"))

def has_error(line):
    # Skip weaver thread content lines — journal/creative text, not real errors
    stripped = line.strip()
    if stripped.startswith("- ") and "[Weaver]" not in line:
        return False
    if stripped.startswith("[Weaver]   - "):
        return False
    if stripped.startswith("[Weaver] Woven:"):
        return False
    if stripped.startswith("[Weaver] Weaving"):
        return False
    # Skip lines with quoted content (likely creative/journal text)
    if stripped.count('"') >= 2 and not any(p in stripped for p in ["Traceback", "SyntaxError", "IndentationError"]):
        if any(word in stripped for word in ["narrator", "system and", "error message", "woven", "thread"]):
            return False
    return any(re.search(p, line) for p in ERROR_PATTERNS)

def main():
    seen = load_seen()
    logs = glob.glob("/tmp/cron-*.log")
    new_errors = []
    for log in logs:
        try:
            size = os.path.getsize(log)
            prev_size = seen.get(log, 0)
            if size <= prev_size:
                continue
            content = open(log).read()
            new_content = content[prev_size:]
            seen[log] = size
            errors = [l.strip() for l in new_content.splitlines() if has_error(l)]
            if errors:
                name = os.path.basename(log)
                new_errors.append(f"{name}: {errors[0][:100]}")
        except:
            pass
    save_seen(seen)
    if new_errors:
        msg = "\n".join(new_errors[:5])
        try:
            requests.post(NTFY_URL,
                data=msg.encode(),
                headers={"Title": "Velaris System Error", "Tags": "warning", "Priority": "high"},
                timeout=10)
            print(f"[ErrorWatch] Sent ntfy: {len(new_errors)} error(s)")
        except Exception as e:
            print(f"[ErrorWatch] ntfy failed: {e}")
    else:
        print(f"[ErrorWatch] No new errors")

if __name__ == "__main__":
    main()
