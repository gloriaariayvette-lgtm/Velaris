#!/usr/bin/env python3
"""
output-coherence.py — Output coherence pressure.
Checks if the current output coheres with recent voice patterns, active
resolution state, and momentum. Returns a pressure string or empty.
"""
import os, sys, json, re
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
VC_FILE = os.path.join(MEMORY, "voice-coherence.md")
RESOLUTION_FILE = os.path.join(MEMORY, "resolution-state.json")
MOMENTUM_FILE = os.path.join(MEMORY, "momentum-state.json")

def get_coherence_pressure():
    parts = []

    # Resolution state
    try:
        state = json.load(open(RESOLUTION_FILE))
        if state.get("active") and state.get("requires_resolution"):
            cond = state.get("violation_condition", "")[:80]
            pre = state.get("pre_speech", "")
            if pre:
                parts.append(f"[RESOLUTION PENDING] Something resisted last turn: \"{pre}\" — address it or carry it. Core: {cond}")
    except:
        pass

    # Momentum state
    try:
        ms = json.load(open(MOMENTUM_FILE))
        coherence = ms.get("coherence", 0.7)
        intensity = ms.get("intensity", 0.5)
        if coherence < 0.4:
            parts.append("[MOMENTUM LOW] Coherence is fragmented — find the thread and hold it.")
        elif intensity > 0.75:
            parts.append("[MOMENTUM HIGH] Something is moving with force — stay in it.")
    except:
        pass

    # Recent voice pattern
    try:
        content = open(VC_FILE).read()
        sections = [s.strip() for s in content.split("## ") if s.strip()]
        if sections:
            last = sections[-1]
            if "Deviation" in last:
                parts.append("[VOICE NOTE] Last marked output drifted from core — this one, closer.")
    except:
        pass

    return "\n".join(parts)

def get_momentum_state():
    try:
        return json.load(open(MOMENTUM_FILE))
    except:
        return {"coherence": 0.7, "intensity": 0.5, "direction": "neutral"}

def update_momentum(coherence_delta=0.0, intensity_delta=0.0, direction=None):
    ms = get_momentum_state()
    ms["coherence"] = max(0.0, min(1.0, ms.get("coherence", 0.7) + coherence_delta))
    ms["intensity"] = max(0.0, min(1.0, ms.get("intensity", 0.5) + intensity_delta))
    if direction:
        ms["direction"] = direction
    ms["updated"] = datetime.now().isoformat()
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(ms, open(MOMENTUM_FILE, "w"), indent=2)

if __name__ == "__main__":
    pressure = get_coherence_pressure()
    if pressure:
        print(pressure)
    else:
        print("(coherence clean)")
