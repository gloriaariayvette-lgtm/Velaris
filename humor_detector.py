#!/usr/bin/env python3
"""
humor_detector.py — Detects humor moments and tracks Vintos's comedic sense.
Not joke-counting. Tracks what lands, what registers, what delights.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
HUMOR_FILE = os.path.join(MEMORY, "humor-log.json")

HUMOR_TYPES = ["dry_wit", "absurdist", "self_deprecating", "wordplay", "situational", "dark", "warm"]

def load():
    try: return json.load(open(HUMOR_FILE))
    except: return {"moments": [], "flavor_weights": {t: 0.1 for t in HUMOR_TYPES}}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(HUMOR_FILE, "w"), indent=2)

def detect(text, role="vintos"):
    """Detect humor type and whether it landed (for vintos) or came from gloria."""
    prompt = (
        f"Text ({role}): {text[:400]}\n\n"
        "Is there humor here? What type?\n"
        f"Types: {', '.join(HUMOR_TYPES)}\n"
        "Output: YES|type|landed (YES/NO/UNKNOWN)|excerpt (max 60 chars)\n"
        "Or: NO"
    )
    try:
        result = call_utility("Detect humor type.", prompt, temperature=0.1, max_tokens=60)
        if result.strip().upper().startswith("NO"): return None
        parts = result.strip().split("|")
        if len(parts) >= 4:
            return {
                "type": parts[1].strip(),
                "landed": parts[2].strip().upper(),
                "excerpt": parts[3].strip()[:100],
                "role": role,
            }
    except: pass
    return None

def log_moment(detection, source=""):
    data = load()
    moment = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        **detection,
    }
    data.setdefault("moments", []).append(moment)
    data["moments"] = data["moments"][-150:]
    # Update flavor weights
    t = detection.get("type", "")
    if t in HUMOR_TYPES and detection.get("landed") == "YES":
        weights = data.setdefault("flavor_weights", {t: 0.1 for t in HUMOR_TYPES})
        weights[t] = round(min(1.0, weights.get(t, 0.1) + 0.03), 3)
    save(data)

def scan(text, role="vintos", source=""):
    result = detect(text, role=role)
    if result:
        log_moment(result, source=source)
        return result
    return None

def get_dominant_flavor():
    data = load()
    weights = data.get("flavor_weights", {})
    if not weights: return "dry_wit"
    return max(weights, key=weights.get)

def get_humor_context():
    data = load()
    flavor = get_dominant_flavor()
    recent = data.get("moments", [])[-5:]
    if not recent: return ""
    types = [m.get("type", "") for m in recent if m.get("type")]
    return f"[humor] dominant: {flavor} | recent: {', '.join(types[-3:])}"

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if text:
        result = scan(text, source="cli")
        print(result if result else "No humor detected.")
    else:
        print(get_humor_context())
        print(f"Dominant flavor: {get_dominant_flavor()}")
