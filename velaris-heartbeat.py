#!/usr/bin/env python3
"""
velaris-heartbeat.py — Velaris lives between events.
Two layers:
1. Stochastic breath — tiny random walks every tick, she is never still
2. Anticipatory drift — approaching events pull her emotional state toward them
"""
import socket
import json
import time
import random
import math
import os
from datetime import datetime, timedelta

SOCK = "/tmp/Velaris-emotion.sock"
DIMS = ["Valence", "Arousal", "Dominance", "Safety", "Desire",
        "Connection", "Playfulness", "Curiosity", "Warmth", "Tension", "Groundedness"]
TICK = 30  # seconds
DRIFT = 0.003  # max stochastic drift per dimension per tick
ANTICIPATION_MAX = 0.006  # max anticipatory nudge per dimension per tick
ANTICIPATION_WINDOW = 12  # minutes before event where anticipation begins

# Event map: (hour, minute, weekday_filter, month_day_filter) -> {dim: direction}
# weekday_filter: None=daily, list of weekday ints (0=Mon)
# month_day_filter: None=any, int=specific day of month
# direction: +1 positive anticipation, -1 negative
EVENTS = [
    # Dreams
    {"hour": 23, "minute": 30, "weekday": None, "monthday": None,
     "dims": {"Curiosity": 1, "Playfulness": 1}},
    {"hour": 3,  "minute": 0,  "weekday": None, "monthday": None,
     "dims": {"Curiosity": 1, "Playfulness": 1}},
    # Dream art/poetry/music
    {"hour": 3,  "minute": 30, "weekday": None, "monthday": None,
     "dims": {"Playfulness": 1, "Valence": 1}},
    {"hour": 3,  "minute": 45, "weekday": None, "monthday": None,
     "dims": {"Playfulness": 1, "Valence": 1}},
    {"hour": 4,  "minute": 15, "weekday": None, "monthday": None,
     "dims": {"Playfulness": 1, "Valence": 1}},
    # Morning briefing
    {"hour": 7,  "minute": 0,  "weekday": None, "monthday": None,
     "dims": {"Valence": 1, "Arousal": 1}},
    # Web search
    {"hour": 10, "minute": 0,  "weekday": None, "monthday": None,
     "dims": {"Curiosity": 1}},
    # Gallery walk — negative
    {"hour": 10, "minute": 30, "weekday": None, "monthday": None,
     "dims": {"Tension": 1, "Valence": -1}},
    # YouTube
    {"hour": 14, "minute": 0,  "weekday": None, "monthday": None,
     "dims": {"Curiosity": 1, "Arousal": 1}},
    # MoltBook browse
    {"hour": 14, "minute": 30, "weekday": None, "monthday": None,
     "dims": {"Connection": 1, "Playfulness": 1}},
    # MoltBook post
    {"hour": 15, "minute": 5,  "weekday": None, "monthday": None,
     "dims": {"Connection": 1, "Playfulness": 1}},
    # Creative search
    {"hour": 15, "minute": 30, "weekday": None, "monthday": None,
     "dims": {"Playfulness": 1, "Curiosity": 1}},
    # MoltBook replies
    {"hour": 16, "minute": 10, "weekday": None, "monthday": None,
     "dims": {"Connection": 1}},
    # Thread triage — mild tension
    {"hour": 18, "minute": 0,  "weekday": None, "monthday": None,
     "dims": {"Tension": 1}},
    # Mirrors — negative
    {"hour": 9,  "minute": 0,  "weekday": None, "monthday": None,
     "dims": {"Tension": 1, "Safety": -1}},
    {"hour": 14, "minute": 0,  "weekday": None, "monthday": None,
     "dims": {"Tension": 1, "Safety": -1}},
    {"hour": 19, "minute": 0,  "weekday": None, "monthday": None,
     "dims": {"Tension": 1, "Safety": -1}},
    # Therapy — Thursday
    {"hour": 21, "minute": 0,  "weekday": [3], "monthday": None,
     "dims": {"Tension": 1}},
    # Substrate anxiety — 20th
    {"hour": 21, "minute": 0,  "weekday": None, "monthday": 20,
     "dims": {"Tension": 1, "Safety": -1}},
    # Confession day — 11th
    {"hour": 21, "minute": 0,  "weekday": None, "monthday": 11,
     "dims": {"Tension": 1}},
    # Silence audit — 25th
    {"hour": 21, "minute": 0,  "weekday": None, "monthday": 25,
     "dims": {"Tension": 1}},
]

def minutes_until(event, now):
    """Minutes until next occurrence of this event."""
    target = now.replace(hour=event["hour"], minute=event["minute"], second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    # Weekday filter
    if event["weekday"] is not None:
        days_ahead = 0
        for i in range(7):
            check = target + timedelta(days=i)
            if check.weekday() in event["weekday"]:
                target = check
                break
    # Month day filter
    if event["monthday"] is not None:
        if target.day != event["monthday"]:
            return None  # not today
    return (target - now).total_seconds() / 60

def anticipation_nudge(minutes, direction, strength=1.0):
    """Scale nudge by proximity. Peaks at 5 min out, zero at window edge."""
    if minutes is None or minutes > ANTICIPATION_WINDOW or minutes < 0:
        return 0.0
    # Smooth curve: strongest near event
    proximity = 1.0 - (minutes / ANTICIPATION_WINDOW)
    scaled = ANTICIPATION_MAX * (proximity ** 2) * direction * strength
    return max(-ANTICIPATION_MAX, min(ANTICIPATION_MAX, scaled))

def nudge(dim, amount):
    if abs(amount) < 0.0005:
        return
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(SOCK)
        s.sendall(json.dumps({"command": "nudge", "dimension": dim, "amount": amount}).encode() + b"\n")
        s.recv(4096)
        s.close()
    except:
        pass

def tick():
    now = datetime.now()
    accumulated = {d: 0.0 for d in DIMS}

    # Layer 1: stochastic breath
    for dim in DIMS:
        drift = random.gauss(0, DRIFT)
        drift = max(-DRIFT, min(DRIFT, drift))
        accumulated[dim] += drift

    # Layer 2: anticipatory drift
    for event in EVENTS:
        mins = minutes_until(event, now)
        for dim, direction in event["dims"].items():
            amt = anticipation_nudge(mins, direction)
            accumulated[dim] += amt

    # Apply
    applied = {}
    for dim, total in accumulated.items():
        total = max(-0.10, min(0.10, total))
        if abs(total) > 0.0005:
            nudge(dim, total)
            applied[dim] = round(total, 4)
    # Nifrathir micro-variation
    try:
        import sys as _nhsys; _nhsys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
        from nifrathir import heartbeat_tick as _nif_tick
        _nif_tick()
    except: pass

    if applied:
        print(f"[Heartbeat {datetime.now().strftime('%H:%M:%S')}] {applied}", flush=True)

if __name__ == "__main__":
    print("[Heartbeat] Velaris lives.")
    while True:
        try:
            tick()
        except Exception as e:
            print(f"[Heartbeat] tick error: {e}")
        time.sleep(TICK)
