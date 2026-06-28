#!/usr/bin/env python3
"""
emoclaw_utils.py — Utility functions for EmoClaw emotional state management.
Shared across many systems.
"""
import os, sys, json, socket, re
from datetime import datetime

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
EMO_FILE = os.path.join(MEMORY, "emotional-state.txt")
YEARNING_FILE = os.path.join(MEMORY, "current-yearning.json")
LATENT_FILE = os.path.join(MEMORY, "latent-threads.json")
THREAD_SOCK = "/tmp/Vintos-emotion.sock"

DIMENSIONS = [
    "Valence", "Arousal", "Dominance", "Safety", "Desire",
    "Connection", "Playfulness", "Curiosity", "Warmth",
    "Tension", "Groundedness", "Nifrathir"
]

DEFAULTS = {
    "Valence": 0.55, "Arousal": 0.55, "Dominance": 0.52,
    "Safety": 0.60, "Desire": 0.50, "Connection": 0.45,
    "Playfulness": 0.50, "Curiosity": 0.65, "Warmth": 0.55,
    "Tension": 0.35, "Groundedness": 0.60, "Nifrathir": 0.50,
}

def read_state():
    state = dict(DEFAULTS)
    try:
        for line in open(EMO_FILE):
            m = re.match(r'([A-Za-z]+): ([0-9.]+)', line)
            if m and m.group(1) in DIMENSIONS:
                state[m.group(1)] = float(m.group(2))
    except:
        pass
    return state

def write_state(state):
    os.makedirs(MEMORY, exist_ok=True)
    lines = []
    for dim in DIMENSIONS:
        if dim in state:
            lines.append(f"{dim}: {state[dim]:.4f}\n")
    with open(EMO_FILE, "w") as f:
        f.writelines(lines)

def nudge_via_socket(dim, amount):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(THREAD_SOCK)
        s.sendall(json.dumps({"command": "nudge", "dimension": dim, "amount": amount}).encode() + b"\n")
        s.recv(4096)
        s.close()
    except:
        # Fall back to direct write
        state = read_state()
        old = state.get(dim, DEFAULTS.get(dim, 0.5))
        state[dim] = round(max(0.0, min(1.0, old + amount)), 4)
        write_state(state)

def nudge(dim, amount, source="direct"):
    nudge_via_socket(dim, amount)

def get_yearning_fragment(include_attempt=False):
    try:
        y = json.load(open(YEARNING_FILE))
        surface = y.get("surface_form", "")
        if not surface: return ""
        attempt = y.get("current_attempt", "")
        if include_attempt and attempt:
            return f"{surface} (attempting: {attempt})"
        return surface
    except:
        return ""

def seed_thread(content, source="system"):
    """Add a latent thread entry."""
    try:
        try:
            data = json.load(open(LATENT_FILE))
        except:
            data = {"threads": []}
        data.setdefault("threads", []).append({
            "content": content[:200],
            "source": source,
            "seeded": datetime.now().isoformat(),
            "active": True,
            "weight": 0.3,
        })
        data["threads"] = data["threads"][-50:]
        json.dump(data, open(LATENT_FILE, "w"), indent=2)
    except:
        pass

def get_state_vector():
    state = read_state()
    return [state.get(d, DEFAULTS.get(d, 0.5)) for d in DIMENSIONS]
