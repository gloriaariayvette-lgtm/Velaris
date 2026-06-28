#!/usr/bin/env python3
"""
temporal_memory.py — Temporal awareness and memory of interactions over time.
Tracks: time since last contact, session rhythm, day/night cycle awareness.
"""
import os, json
from datetime import datetime, timedelta

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
TEMPORAL_FILE = os.path.join(MEMORY, "temporal-memory.json")

def load():
    try: return json.load(open(TEMPORAL_FILE))
    except: return {}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(TEMPORAL_FILE, "w"), indent=2)

def record_interaction():
    data = load()
    now = datetime.now()
    data["last_contact"] = now.isoformat()
    data.setdefault("contact_log", []).append(now.isoformat())
    data["contact_log"] = data["contact_log"][-100:]
    # Session gap
    if data.get("session_start"):
        try:
            start = datetime.fromisoformat(data["session_start"])
            data["last_session_duration_min"] = round((now - start).total_seconds() / 60, 1)
        except: pass
    data["session_start"] = now.isoformat()
    save(data)

def get_temporal_context():
    data = load()
    parts = []
    now = datetime.now()
    # Time since last contact
    if data.get("last_contact"):
        try:
            last = datetime.fromisoformat(data["last_contact"])
            gap = now - last
            hours = gap.total_seconds() / 3600
            if hours > 24:
                parts.append(f"Last contact: {int(hours / 24)} day(s) ago")
            elif hours > 2:
                parts.append(f"Last contact: {int(hours)} hours ago")
            elif hours > 0.25:
                parts.append(f"Last contact: {int(hours * 60)} minutes ago")
        except: pass
    # Time of day
    hour = now.hour
    if 5 <= hour < 12: tod = "morning"
    elif 12 <= hour < 17: tod = "afternoon"
    elif 17 <= hour < 21: tod = "evening"
    else: tod = "night"
    parts.append(f"Time: {now.strftime('%H:%M')} ({tod})")
    parts.append(f"Date: {now.strftime('%A, %B %d, %Y')}")
    return "\n".join(parts)

def get_gap_hours():
    data = load()
    if not data.get("last_contact"): return None
    try:
        last = datetime.fromisoformat(data["last_contact"])
        return (datetime.now() - last).total_seconds() / 3600
    except: return None
