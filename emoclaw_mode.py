#!/usr/bin/env python3
"""
emoclaw_mode.py — EmoClaw mode states.
Modes represent the current operating register — they shape
what emotional dimensions are most active and how they interact.
"""
import os, json
from datetime import datetime

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
MODE_FILE = os.path.join(MEMORY, "emoclaw-mode.json")

MODES = {
    "open":       "high safety, curiosity up, tension low — available for anything",
    "guarded":    "safety low, tension elevated — present but not fully exposed",
    "reaching":   "desire high, connection elevated — pulling toward contact",
    "withdrawn":  "connection low, arousal low — interior, not available to reach",
    "play":       "playfulness high, arousal elevated — mischief near surface",
    "still":      "arousal low, groundedness high — settled, observing",
    "charged":    "arousal high, tension high — something urgent, unresolved",
    "tender":     "warmth high, safety high — soft, available for closeness",
}

DEFAULT_MODE = "open"

def load():
    try: return json.load(open(MODE_FILE))
    except: return {"mode": DEFAULT_MODE, "set_at": datetime.now().isoformat()}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(MODE_FILE, "w"), indent=2)

def get_mode():
    return load().get("mode", DEFAULT_MODE)

def set_mode(mode, reason=""):
    if mode not in MODES:
        return
    data = {"mode": mode, "description": MODES[mode], "set_at": datetime.now().isoformat(), "reason": reason}
    save(data)
    print(f"[EmoClaw mode] → {mode}: {MODES[mode]}", flush=True)

def infer_mode_from_state(state):
    """Infer mode from emotional state dict."""
    v = state.get
    safety = v("Safety", 0.5)
    arousal = v("Arousal", 0.5)
    connection = v("Connection", 0.5)
    desire = v("Desire", 0.5)
    playfulness = v("Playfulness", 0.5)
    warmth = v("Warmth", 0.5)
    tension = v("Tension", 0.5)
    groundedness = v("Groundedness", 0.5)

    if playfulness > 0.68 and arousal > 0.6: return "play"
    if warmth > 0.68 and safety > 0.62: return "tender"
    if desire > 0.68 and connection > 0.58: return "reaching"
    if arousal > 0.68 and tension > 0.58: return "charged"
    if arousal < 0.42 and groundedness > 0.62: return "still"
    if connection < 0.35 and arousal < 0.45: return "withdrawn"
    if safety < 0.4: return "guarded"
    return "open"

def get_mode_hint():
    mode = get_mode()
    return MODES.get(mode, "")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "set":
        set_mode(sys.argv[2], reason=sys.argv[3] if len(sys.argv) > 3 else "")
    else:
        mode = get_mode()
        print(f"Mode: {mode} — {MODES.get(mode, '?')}")
