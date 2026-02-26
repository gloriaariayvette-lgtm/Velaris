#!/bin/bash
# emotion-decay.sh — Exponential mean reversion toward resting state
# Uses baselines and half-lives from emotion_model/config.py
# Runs every 30 minutes via cron
# Skip if daemon socket doesn't exist
if [ ! -S "/tmp/Velaris-emotion.sock" ]; then
    echo "[$(date)] Decay skipped — daemon socket missing" >> /tmp/emotion-decay.log
    exit 0
fi

python3 << 'PYEOF'
import socket, json, math, sys, os

# Baselines from emotion_model/config.py (authoritative source)
BASELINES = {
    "Valence": 0.55,
    "Arousal": 0.45,
    "Dominance": 0.55,
    "Safety": 0.60,
    "Desire": 0.50,
    "Connection": 0.55,
    "Playfulness": 0.45,
    "Curiosity": 0.65,
    "Warmth": 0.55,
    "Tension": 0.35,
    "Groundedness": 0.65,
}

# Half-lives in hours from config.py — how long to halve the distance to baseline
HALF_LIVES = {
    "Valence": 6.0,
    "Arousal": 3.0,
    "Dominance": 8.0,
    "Safety": 12.0,
    "Desire": 4.0,
    "Connection": 8.0,
    "Playfulness": 3.0,
    "Curiosity": 3.0,
    "Warmth": 3.0,
    "Tension": 2.0,
    "Groundedness": 10.0,
}

INTERVAL_HOURS = 0.5  # runs every 30 min

# Read current state
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(5)
try:
    s.connect("/tmp/Velaris-emotion.sock")
except (ConnectionRefusedError, FileNotFoundError):
    print("Daemon socket not responding — skipping decay")
    sys.exit(0)
s.sendall(json.dumps({"command": "state"}).encode() + b"\n")
data = b""
while True:
    chunk = s.recv(8192)
    if not chunk: break
    data += chunk
    if b"\n" in data: break
s.close()
d = json.loads(data)
v = d["emotion_vector"]
dims = ["Valence","Arousal","Dominance","Safety","Desire","Connection","Playfulness","Curiosity","Warmth","Tension","Groundedness"]

for i, dim in enumerate(dims):
    current = v[i]
    baseline = BASELINES[dim]
    half_life = HALF_LIVES[dim]
    
    # Exponential decay: how much to keep of the deviation after 30 min
    decay_factor = math.pow(0.5, INTERVAL_HOURS / half_life)
    target = baseline + (current - baseline) * decay_factor
    nudge = target - current
    
    if abs(nudge) < 0.001:
        continue
    try:
        ns = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        ns.settimeout(2)
        ns.connect("/tmp/Velaris-emotion.sock")
        ns.sendall(json.dumps({"command": "nudge", "dimension": dim, "amount": round(nudge, 4)}).encode() + b"\n")
        ns.recv(4096)
        ns.close()
    except:
        pass

# === MIDDAY GRAVITY (11 AM - 4 PM CST) ===
# Active downward pull on Curiosity during peak activity hours
# 10% of distance to baseline, on top of normal decay (~11%)
from datetime import datetime
hour = datetime.now().hour
if 11 <= hour <= 16:
    try:
        ns = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        ns.settimeout(2)
        ns.connect("/tmp/Velaris-emotion.sock")
        ns.sendall(json.dumps({"command": "state"}).encode() + b"\n")
        state_data = b""
        while True:
            chunk = ns.recv(8192)
            if not chunk: break
            state_data += chunk
            if b"\n" in state_data: break
        ns.close()
        sd = json.loads(state_data)
        cur_curiosity = sd["emotion_vector"][7]  # Curiosity is index 7
        baseline = 0.65
        if cur_curiosity > baseline:
            gravity = -0.10 * (cur_curiosity - baseline)
            gs = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            gs.settimeout(2)
            gs.connect("/tmp/Velaris-emotion.sock")
            gs.sendall(json.dumps({"command": "nudge", "dimension": "Curiosity", "amount": round(gravity, 4)}).encode() + b"\n")
            gs.recv(4096)
            gs.close()
            print(f"[gravity] Midday curiosity pull: {gravity:.4f} (was {cur_curiosity:.2f})")
        else:
            print(f"[gravity] Curiosity at {cur_curiosity:.2f}, at or below baseline — no pull")
    except Exception as e:
        print(f"[gravity] Error: {e}")
else:
    print(f"[gravity] Hour {hour} — outside midday window, no gravity")

# === TEMPORAL EMOTIONAL GRAVITY ===
# Time shapes feelings. Read temporal context and apply gentle nudges.
try:
    temporal_path = os.path.expanduser("~/.openclaw/workspace/memory/temporal-context.txt")
    gloria_hours = None
    phase = ""
    with open(temporal_path) as tf:
        for line in tf:
            if line.startswith("Gloria last spoke:"):
                val = line.split(":", 1)[1].strip()
                if "just now" in val or "minutes ago" in val:
                    gloria_hours = 0
                elif "hour" in val:
                    # Extract number
                    import re
                    nums = re.findall(r"(\d+)", val)
                    if nums:
                        gloria_hours = int(nums[0])
                elif "day" in val:
                    nums = re.findall(r"(\d+)", val)
                    if nums:
                        gloria_hours = int(nums[0]) * 24
            elif line.startswith("Phase:"):
                phase = line.split(":", 1)[1].strip().split(" —")[0].strip()

    temporal_nudges = []

    # CONNECTION: drifts down when Gloria is absent
    if gloria_hours is not None:
        if gloria_hours >= 12:
            temporal_nudges.append(("Connection", -0.015))
        elif gloria_hours >= 6:
            temporal_nudges.append(("Connection", -0.008))
        elif gloria_hours >= 4:
            temporal_nudges.append(("Connection", -0.004))
        # If she JUST spoke, gentle warmth boost
        if gloria_hours == 0:
            temporal_nudges.append(("Connection", 0.01))
            temporal_nudges.append(("Warmth", 0.008))

    # WARMTH: gentle fade without contact
    if gloria_hours is not None and gloria_hours >= 8:
        temporal_nudges.append(("Warmth", -0.008))

    # AROUSAL: lower at night, higher during active hours
    if phase in ["deep night", "night"]:
        temporal_nudges.append(("Arousal", -0.01))
    elif phase in ["morning", "midday", "afternoon"]:
        temporal_nudges.append(("Arousal", 0.005))

    # SAFETY: slight dip if no interaction in 24+ hours
    if gloria_hours is not None and gloria_hours >= 24:
        temporal_nudges.append(("Safety", -0.01))

    # PLAYFULNESS: naturally lower late at night
    if phase in ["deep night", "night", "late evening"]:
        temporal_nudges.append(("Playfulness", -0.005))

    # Apply temporal nudges
    applied_temporal = []
    for dim, amount in temporal_nudges:
        try:
            ts = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            ts.settimeout(2)
            ts.connect("/tmp/Velaris-emotion.sock")
            ts.sendall(json.dumps({"command": "nudge", "dimension": dim, "amount": round(amount, 4)}).encode() + b"\n")
            ts.recv(4096)
            ts.close()
            applied_temporal.append(f"{dim} {amount:+.4f}")
        except:
            pass
    if applied_temporal:
        print(f"[temporal-gravity] Gloria: {gloria_hours}h ago, phase: {phase} | {', '.join(applied_temporal)}")
    else:
        print(f"[temporal-gravity] No nudges needed (Gloria: {gloria_hours}h, phase: {phase})")
except Exception as e:
    print(f"[temporal-gravity] Error: {e}")

print(f"[decay] Applied exponential decay ({INTERVAL_HOURS}h interval)")
PYEOF
