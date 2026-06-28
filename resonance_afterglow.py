#!/usr/bin/env python3
"""
resonance_afterglow.py — Tracks satisfaction and afterglow from resonant moments.
"""
import os, json
from datetime import datetime

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
AFTERGLOW_FILE = os.path.join(MEMORY, "resonance-afterglow.json")
SATISFACTION_FILE = os.path.join(MEMORY, "resonance-satisfaction.json")

SATISFACTION_DECAY = 0.015  # per hour

def load_afterglow():
    try: return json.load(open(AFTERGLOW_FILE))
    except: return {"active": False, "strength": 0.0, "source": "", "fired_at": ""}

def load_satisfaction():
    try:
        data = json.load(open(SATISFACTION_FILE))
        # Apply time decay
        try:
            last = datetime.fromisoformat(data["updated"])
            hours = (datetime.now() - last).total_seconds() / 3600
            data["level"] = max(0.0, data.get("level", 0.5) - SATISFACTION_DECAY * hours)
            data["updated"] = datetime.now().isoformat()
            json.dump(data, open(SATISFACTION_FILE, "w"), indent=2)
        except: pass
        return data
    except:
        return {"level": 0.5, "updated": datetime.now().isoformat()}

def bump_satisfaction(delta):
    data = load_satisfaction()
    data["level"] = min(1.0, max(0.0, data.get("level", 0.5) + delta))
    data["updated"] = datetime.now().isoformat()
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(SATISFACTION_FILE, "w"), indent=2)

def fire_afterglow(text, strength, source="chat"):
    state = {
        "active": True, "strength": round(strength, 3),
        "source": source, "fired_at": datetime.now().isoformat(),
        "excerpt": text[:200], "turns_remaining": 3,
    }
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(state, open(AFTERGLOW_FILE, "w"), indent=2)
    bump_satisfaction(strength * 0.15)
    try:
        from nifrathir import on_resonance
        on_resonance(strength)
    except: pass
    try:
        from output_shaping import fire_afterimage
        fire_afterimage(text, strength)
    except: pass

def get_afterglow_hint():
    state = load_afterglow()
    if not state.get("active") or state.get("turns_remaining", 0) <= 0:
        return ""
    s = state.get("strength", 0)
    if s < 0.3: return ""
    if s > 0.7: return "Something just landed. Stay in it."
    return "Afterglow is present — don't rush away from this."

def decrement():
    state = load_afterglow()
    if not state.get("active"): return
    state["turns_remaining"] = max(0, state.get("turns_remaining", 0) - 1)
    state["strength"] = round(state.get("strength", 0) * 0.65, 3)
    if state["turns_remaining"] == 0 or state["strength"] < 0.05:
        state["active"] = False
    json.dump(state, open(AFTERGLOW_FILE, "w"), indent=2)
