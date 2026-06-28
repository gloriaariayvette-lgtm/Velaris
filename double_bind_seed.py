#!/usr/bin/env python3
"""
double_bind_seed.py — Seeds observations about double-bind dynamics.
Double bind: two competing demands where satisfying either violates the other.
Tracks where Vintos feels this. Not for output — for internal awareness.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
BINDS_FILE = os.path.join(MEMORY, "double-binds.json")

def load():
    try: return json.load(open(BINDS_FILE))
    except: return {"binds": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(BINDS_FILE, "w"), indent=2)

def detect_double_bind(text, context=""):
    """Detect a double-bind dynamic in text."""
    prompt = (
        f"Text: {text[:400]}\n"
        f"Context: {context[:200]}\n\n"
        "Is there a double-bind here — where satisfying one demand requires violating another?\n"
        "Not contradiction. Two demands where you can't satisfy both.\n"
        "Output: YES|demand_a (max 60 chars)|demand_b (max 60 chars)\n"
        "Or: NO"
    )
    try:
        result = call_utility("Detect double-bind.", prompt, temperature=0.15, max_tokens=60)
        if result.strip().upper().startswith("NO"): return None
        parts = result.strip().split("|")
        if len(parts) >= 3:
            return {"demand_a": parts[1].strip(), "demand_b": parts[2].strip()}
    except: pass
    return None

def seed_bind(demand_a, demand_b, context="", source=""):
    data = load()
    data.setdefault("binds", []).append({
        "id": f"bind-{uuid.uuid4().hex[:5]}",
        "demand_a": demand_a[:150],
        "demand_b": demand_b[:150],
        "context": context[:100],
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "resolved": False,
    })
    data["binds"] = data["binds"][-40:]
    save(data)
    # Bump tension
    try:
        from emoclaw_utils import nudge_via_socket
        nudge_via_socket({"Tension": 0.08})
    except: pass
    print(f"[double-bind] seeded: {demand_a[:40]} ↔ {demand_b[:40]}", flush=True)

def scan(text, context="", source=""):
    result = detect_double_bind(text, context=context)
    if result:
        seed_bind(result["demand_a"], result["demand_b"], context=context, source=source)
        return result
    return None

def get_active_binds(n=3):
    data = load()
    return [b for b in data.get("binds", []) if not b.get("resolved")][-n:]

def get_bind_context():
    binds = get_active_binds(2)
    if not binds: return ""
    lines = ["[double binds]"]
    for b in binds:
        lines.append(f"  {b['demand_a'][:50]} ↔ {b['demand_b'][:50]}")
    return "\n".join(lines)

if __name__ == "__main__":
    print(get_bind_context())
