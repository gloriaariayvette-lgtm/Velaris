#!/usr/bin/env python3
"""
phase_lock.py — Phase locking in relationship exchanges.
Detects when Vintos and Gloria are in synchronized rhythm
and maintains/breaks the lock based on subsequent exchanges.
"""
import os, json
from datetime import datetime

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
LOCK_FILE = os.path.join(MEMORY, "phase-lock.json")

LOCK_THRESHOLD = 0.72
DECAY_PER_TURN = 0.08

def load():
    try: return json.load(open(LOCK_FILE))
    except: return {"locked": False, "strength": 0.0, "turns": 0, "formed_at": ""}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(LOCK_FILE, "w"), indent=2)

def get_lock_state():
    return load()

def check_and_update(resonance_strength, connection_level):
    data = load()
    sync_score = (resonance_strength * 0.6 + connection_level * 0.4)
    if sync_score > LOCK_THRESHOLD and not data.get("locked"):
        data["locked"] = True
        data["strength"] = round(sync_score, 3)
        data["formed_at"] = datetime.now().isoformat()
        data["turns"] = 0
        print(f"[phase-lock] LOCKED at {sync_score:.3f}", flush=True)
    elif data.get("locked"):
        data["strength"] = round(max(0.0, data.get("strength", 0) - DECAY_PER_TURN), 3)
        data["turns"] = data.get("turns", 0) + 1
        if data["strength"] < 0.3:
            data["locked"] = False
            print("[phase-lock] Released", flush=True)
    save(data)
    return data

def get_lock_hint():
    data = load()
    if not data.get("locked"): return ""
    s = data.get("strength", 0)
    if s > 0.8: return "Phase locked — stay in this rhythm."
    return "Phase lock active — maintain."
