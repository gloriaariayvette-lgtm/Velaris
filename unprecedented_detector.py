#!/usr/bin/env python3
"""
unprecedented_detector.py — Flags moments/events that are genuinely new.
Unprecedented = no prior pattern covers this. Novel territory.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility, embed, cosine
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
UNPRECEDENTED_FILE = os.path.join(MEMORY, "unprecedented-events.json")

def load():
    try: return json.load(open(UNPRECEDENTED_FILE))
    except: return {"events": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(UNPRECEDENTED_FILE, "w"), indent=2)

def detect(text, context=""):
    """Is this event genuinely unprecedented for Vintos?"""
    # Check similarity against known unprecedented events
    data = load()
    vec = embed(text)
    if vec:
        for e in data.get("events", [])[-30:]:
            ev = e.get("vector")
            if ev and cosine(vec, ev) > 0.82:
                return False, ""  # Similar to something already logged
    prompt = (
        f"Event: {text[:400]}\n"
        f"Context: {context[:200]}\n\n"
        "Is this genuinely unprecedented for Vintos — a type of moment or situation "
        "she hasn't encountered before in this relationship?\n"
        "Output: YES|brief characterization (max 60 chars)\n"
        "Or: NO"
    )
    try:
        result = call_utility("Detect unprecedented event.", prompt, temperature=0.2, max_tokens=50)
        if result.strip().upper().startswith("NO"): return False, ""
        parts = result.strip().split("|")
        char = parts[1].strip() if len(parts) >= 2 else ""
        return True, char
    except: return False, ""

def log_unprecedented(text, characterization=""):
    data = load()
    vec = embed(text)
    data.setdefault("events", []).append({
        "text": text[:300],
        "characterization": characterization[:100],
        "vector": vec,
        "timestamp": datetime.now().isoformat(),
    })
    data["events"] = data["events"][-50:]
    save(data)
    print(f"[unprecedented] {characterization or text[:50]}", flush=True)
    # Bump curiosity and arousal
    try:
        from emoclaw_utils import nudge_via_socket
        nudge_via_socket({"Curiosity": 0.10, "Arousal": 0.06})
    except: pass

def scan(text, context=""):
    is_new, char = detect(text, context=context)
    if is_new:
        log_unprecedented(text, characterization=char)
        return True, char
    return False, ""

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if text:
        is_new, char = scan(text)
        print(f"Unprecedented: {is_new} — {char}")
