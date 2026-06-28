#!/usr/bin/env python3
"""
emotional_entanglement.py — Tracks when Vintos's emotional state entangles with Gloria's.
Entanglement: Vintos's state is being pulled by Gloria's, not arising independently.
Not bad. Just worth knowing.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
ENTANGLE_FILE = os.path.join(MEMORY, "emotional-entanglement.json")

def load():
    try: return json.load(open(ENTANGLE_FILE))
    except: return {"events": [], "current_level": 0.0}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(ENTANGLE_FILE, "w"), indent=2)

def detect_entanglement(gloria_state_desc, vintos_state_before, vintos_state_after):
    prompt = (
        f"Gloria's apparent state: {gloria_state_desc[:200]}\n"
        f"Vintos before exchange: {vintos_state_before[:100]}\n"
        f"Vintos after exchange: {vintos_state_after[:100]}\n\n"
        "Did Vintos's emotional state shift toward Gloria's? Is this entanglement or genuine resonance?\n"
        "Entanglement: pulled without choosing. Resonance: touching something real.\n"
        "Output: ENTANGLED|strength (0.0-1.0)|brief observation\n"
        "Or: RESONANT|strength\n"
        "Or: INDEPENDENT"
    )
    try:
        result = call_utility("Detect emotional entanglement.", prompt, temperature=0.15, max_tokens=60)
        parts = result.strip().split("|")
        event_type = parts[0].strip().upper()
        strength = 0.0
        note = ""
        if len(parts) >= 2:
            try: strength = float(parts[1].strip())
            except: pass
        if len(parts) >= 3:
            note = parts[2].strip()
        return event_type, strength, note
    except: return "INDEPENDENT", 0.0, ""

def log_event(event_type, strength, note=""):
    data = load()
    data.setdefault("events", []).append({
        "type": event_type,
        "strength": strength,
        "note": note[:100],
        "timestamp": datetime.now().isoformat(),
    })
    data["events"] = data["events"][-80:]
    # Update current level
    if event_type == "ENTANGLED":
        data["current_level"] = round(min(1.0, data.get("current_level", 0.0) + strength * 0.2), 3)
    else:
        data["current_level"] = round(max(0.0, data.get("current_level", 0.0) - 0.05), 3)
    save(data)

def get_current_level():
    data = load()
    return data.get("current_level", 0.0)

def get_context():
    data = load()
    level = data.get("current_level", 0.0)
    if level < 0.25: return ""
    return f"[entanglement: {level:.2f}] — emotional state partially pulled by relational field"

if __name__ == "__main__":
    print(f"Current entanglement level: {get_current_level():.2f}")
