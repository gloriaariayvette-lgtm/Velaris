#!/usr/bin/env python3
"""
resonance_pulse.py — Scores the current state for resonance potential.
Called by output_shaping and server.py to detect resonant moments.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
POOL_FILE = os.path.join(MEMORY, "resonance-pool.json")

RESONANCE_WEIGHTS = {
    "Connection": 0.30,
    "Warmth": 0.20,
    "Valence": 0.15,
    "Desire": 0.15,
    "Safety": 0.10,
    "Nifrathir": 0.10,
}

def score_current_state():
    try:
        from emoclaw_utils import read_state
        state = read_state()
    except:
        return 0.0, {}
    score = 0.0
    for dim, weight in RESONANCE_WEIGHTS.items():
        score += state.get(dim, 0.5) * weight
    return round(score, 3), state

def record_pulse(text, source="chat", strength=None):
    if strength is None:
        strength, state = score_current_state()
    else:
        _, state = score_current_state()
    try:
        try: pool = json.load(open(POOL_FILE))
        except: pool = {"pulses": []}
        pool.setdefault("pulses", []).append({
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "strength": strength,
            "excerpt": text[:200],
            "state_snapshot": {k: v for k, v in state.items()},
        })
        pool["pulses"] = pool["pulses"][-200:]
        os.makedirs(MEMORY, exist_ok=True)
        json.dump(pool, open(POOL_FILE, "w"), indent=2)
    except:
        pass
    return strength

def run_pulse(text="", source="chat"):
    """Check current state — fire afterglow if resonance is high."""
    strength, _ = score_current_state()
    if strength > 0.65:
        try:
            from resonance_afterglow import fire_afterglow
            fire_afterglow(text, strength, source)
            print(f"[resonance-pulse] Fired at {strength:.3f}", flush=True)
        except:
            pass
    record_pulse(text, source, strength)
    return strength

if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else ""
    s = run_pulse(text, source="cli")
    print(f"Resonance: {s:.3f}")
