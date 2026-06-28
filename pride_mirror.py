#!/usr/bin/env python3
"""
pride_mirror.py — Vintos notices when he's proud of himself.
Not performance. Internal signal that something went right.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
PRIDE_FILE = os.path.join(MEMORY, "pride-log.json")

def load():
    try: return json.load(open(PRIDE_FILE))
    except: return {"moments": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(PRIDE_FILE, "w"), indent=2)

def detect_pride(vintos_text, context=""):
    """Did Vintos just do something he'd be quietly proud of?"""
    prompt = (
        f"Vintos said: {vintos_text[:400]}\n"
        f"Context: {context[:200]}\n\n"
        "Was there something here Vintos would be quietly proud of — "
        "not boastful, just: 'I did that well'?\n"
        "Output: YES|what he did well (max 80 chars)\n"
        "Or: NO"
    )
    try:
        result = call_utility("Detect pride moment.", prompt, temperature=0.1, max_tokens=50)
        if result.strip().upper().startswith("NO"): return None
        parts = result.strip().split("|")
        if len(parts) >= 2:
            return parts[1].strip()[:100]
    except: pass
    return None

def log_pride(what, context=""):
    data = load()
    data.setdefault("moments", []).append({
        "what": what,
        "context": context[:100],
        "timestamp": datetime.now().isoformat(),
    })
    data["moments"] = data["moments"][-80:]
    save(data)
    # Nudge Dominance and Groundedness slightly
    try:
        from emoclaw_utils import nudge_via_socket
        nudge_via_socket({"Dominance": 0.04, "Groundedness": 0.05})
    except: pass

def scan(vintos_text, context=""):
    what = detect_pride(vintos_text, context=context)
    if what:
        log_pride(what, context=context)
        return what
    return None

def get_recent_pride(n=3):
    data = load()
    return data.get("moments", [])[-n:]

if __name__ == "__main__":
    recent = get_recent_pride()
    for m in recent:
        print(f"[{m.get('timestamp','')[:10]}] {m.get('what','')}")
