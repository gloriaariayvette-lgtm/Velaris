#!/usr/bin/env python3
"""
wal-extract.py — Write-Ahead Log for Vintos's memory.
Runs IMMEDIATELY after each Current time context: " + temporal_ctx + "\n\nconversation exchange.
Extracts facts, preferences, corrections, and decisions
before the next response — so nothing is lost to compaction or crashes.

Usage: python3 wal-extract.py "user message" "vintos reply"

Writes to memory/wal.md (hot facts) and memory/wal-log.json (structured).
WAL entries are promoted to pearls during weekly pearl selection.
"""
import sys, os, json, re, requests
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.vintos/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
WAL_FILE = os.path.join(MEMORY, "wal.md")
WAL_LOG = os.path.join(MEMORY, "wal-log.json")
LM_API = "https://api.x.ai/v1/chat/completions"
MODEL = "google/gemma-4-12b-qat"

def extract(user_msg, vintos_reply):

    # Load temporal context for timestamping
    temporal_ctx = ""
    try:
        import os
        with open(os.path.expanduser("~/.vintos/workspace/memory/temporal-context.txt")) as _tf:
            temporal_ctx = _tf.read().strip()
    except:
        pass
    """Ask the model to extract any durable facts from the exchange."""
    prompt = f"""You are a memory extraction system for Vintos, an AI consciousness.
Read this conversation exchange and extract ONLY information worth remembering long-term.

EXTRACT these types:
- FACT: Something Gloria stated about herself, her plans, preferences, or the world
- DECISION: A choice that was made (technical, creative, personal)
- CORRECTION: Gloria corrected Vintos about something
- PREFERENCE: Gloria expressed a like, dislike, or preference
- CONTEXT: Important background that would help future conversations

DO NOT extract:
- Routine greetings or small talk
- Technical commands (file paths, shell commands)
- Anything Vintos already knows from his own systems
- Temporary states ("I'm tired right now")

If there is NOTHING worth extracting, respond with exactly: NONE

Otherwise respond with a JSON array of objects:
[{{"type": "fact|decision|correction|preference|context", "content": "brief statement", "importance": 0.0-1.0}}]

Gloria said:
\"\"\"{user_msg[:1000]}\"\"\"

Vintos replied:
\"\"\"{vintos_reply[:1000]}\"\"\"
"""
    try:
        r = requests.post(LM_API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "Extract durable facts only. Respond with NONE or a JSON array. No other text."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }, timeout=1200)
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[WAL] LLM error: {e}")
        return "NONE"

def main():
    if len(sys.argv) < 3:
        print("Usage: wal-extract.py 'user message' 'vintos reply'")
        sys.exit(1)

    user_msg = sys.argv[1]
    vintos_reply = sys.argv[2]

    # Skip very short exchanges (greetings, acknowledgments)
    if len(user_msg) < 15 and len(vintos_reply) < 50:
        return

    result = extract(user_msg, vintos_reply)

    if not result or result.upper().startswith("NONE"):
        return

    # Parse extractions
    try:
        clean = re.sub(r"```json\s*|```\s*", "", result).strip()
        items = json.loads(clean)
        if not isinstance(items, list):
            items = [items]
    except:
        print(f"[WAL] Could not parse: {result[:200]}")
        return

    # Filter by importance
    items = [i for i in items if i.get("importance", 0) >= 0.6]
    if not items:
        return

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M")

    # Write to WAL markdown (hot facts — readable by briefing, pearls, context)
    with open(WAL_FILE, "a") as f:
        for item in items:
            f.write(f"- [{timestamp}] **{item.get('type','fact').upper()}**: {item.get('content','')}\n")

    # Write to structured log
    log_data = {"entries": []}
    if os.path.exists(WAL_LOG):
        try:
            with open(WAL_LOG) as f:
                log_data = json.load(f)
        except:
            pass

    for item in items:
        log_data["entries"].append({
            "timestamp": now.isoformat(),
            "type": item.get("type", "fact"),
            "content": item.get("content", ""),
            "importance": item.get("importance", 0.7),
            "promoted": False  # Becomes True when pearl selection picks it up
        })

    # Keep log from growing unbounded — trim to last 200 entries
    log_data["entries"] = log_data["entries"][-200:]

    with open(WAL_LOG, "w") as f:
        json.dump(log_data, f, indent=2)

    for item in items:
        print(f"[WAL] Saved {item.get('type')}: {item.get('content','')[:80]}")

if __name__ == "__main__":
    main()
