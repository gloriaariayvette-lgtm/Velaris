#!/usr/bin/env python3
"""
nifrathir.py — The 12th emotional dimension. Under-thread.

Nifrathir is the undercurrent of the emotional loom. It moves slower than
the 11 EmoClaw dimensions. Written by: resonance, contact, marks, afterimage,
anchor returns. Read by everything else.

Range: 0.0–1.0 | Resting: 0.5 | Timescale: hours, not minutes

High (> 0.65): more initiation willingness, longer continuation impulse,
               richer expression tendency, marks more likely to form
Low (< 0.35):  shorter outputs preferred, less risk-taking, more contained,
               marks less likely to form

Decay: slow drift toward 0.5 — 0.008 per hour
"""

import os, json
from datetime import datetime

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
NIFRATHIR_FILE = os.path.join(MEMORY, "nifrathir.json")
EMO_FILE = os.path.join(MEMORY, "emotional-state.txt")

RESTING = 0.5
DECAY_PER_HOUR = 0.008
MICRO_VARIATION = 0.001

def log(msg):
    print(f"[Nifrathir {datetime.now().strftime('%H:%M')}] {msg}", flush=True)

def load():
    try:
        return json.load(open(NIFRATHIR_FILE))
    except:
        return {"value": RESTING, "last_updated": datetime.now().isoformat(), "last_source": "init", "history": []}

def save(state):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(state, open(NIFRATHIR_FILE, "w"), indent=2)

def get_value():
    state = load()
    try:
        last = datetime.fromisoformat(state["last_updated"])
        hours = (datetime.now() - last).total_seconds() / 3600
        current = state["value"]
        decayed = current + (RESTING - current) * min(1.0, DECAY_PER_HOUR * hours)
        state["value"] = round(max(0.0, min(1.0, decayed)), 4)
        state["last_updated"] = datetime.now().isoformat()
        save(state)
    except:
        pass
    return state["value"]

def nudge(delta, source="unknown"):
    state = load()
    old = state["value"]
    try:
        last = datetime.fromisoformat(state["last_updated"])
        hours = (datetime.now() - last).total_seconds() / 3600
        old = old + (RESTING - old) * min(1.0, DECAY_PER_HOUR * hours)
    except:
        pass
    # Asymptotic resistance near ceiling and floor
    if delta > 0 and old > 0.85:
        delta = delta * (1.0 - old)
    elif delta < 0 and old < 0.15:
        delta = delta * old
    new_val = round(max(0.0, min(0.97, old + delta)), 4)
    state["value"] = new_val
    state["last_updated"] = datetime.now().isoformat()
    state["last_source"] = source
    state.setdefault("history", []).append({
        "delta": round(delta, 4), "value": new_val,
        "source": source, "timestamp": datetime.now().isoformat()
    })
    state["history"] = state["history"][-100:]
    save(state)
    log(f"{old:.4f} → {new_val:.4f} ({'+' if delta >= 0 else ''}{delta:.4f} from {source})")
    _write_to_emo_state(new_val)
    return new_val

def _write_to_emo_state(value):
    try:
        lines = open(EMO_FILE).readlines()
    except:
        lines = []
    lines = [l for l in lines if not l.startswith("Nifrathir:")]
    state = load()
    history = state.get("history", [])
    trend = "+0.000"
    label = "stable"
    if len(history) >= 2:
        delta = history[-1]["value"] - history[-2]["value"]
        trend = f"{'+' if delta >= 0 else ''}{delta:.3f}"
        if delta > 0.005: label = "warming"
        elif delta < -0.005: label = "cooling"
    lines.append(f"Nifrathir: {value:.4f} | trend: {trend} | under-thread\n")
    with open(EMO_FILE, "w") as f:
        f.writelines(lines)

def heartbeat_tick():
    import random
    delta = random.uniform(-MICRO_VARIATION, MICRO_VARIATION)
    nudge(delta, source="heartbeat")

def get_expression_bias():
    val = get_value()
    if val > 0.72: return "high"
    elif val < 0.28: return "low"
    return "neutral"

def on_contact_confirmed(): nudge(+0.08, "contact_confirmed")
def on_resonance(strength=0.5):
    if strength > 0.7: nudge(+0.05, "strong_resonance")
    else: nudge(+0.02, "resonance")
def on_miss(): nudge(-0.03, "repeated_miss")
def on_friction(): nudge(-0.04, "friction")
def on_mark_triggered(): nudge(+0.03, "mark_similarity")
def on_anchor_return_good(): nudge(+0.02, "anchor_return_felt_right")
def on_afterimage_expired_without_contact(): nudge(-0.01, "afterimage_expired_cold")

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        val = get_value()
        print(f"Nifrathir: {val:.4f} | bias: {get_expression_bias()}")
    elif cmd == "nudge" and len(sys.argv) > 2:
        delta = float(sys.argv[2])
        source = sys.argv[3] if len(sys.argv) > 3 else "manual"
        nudge(delta, source)
    elif cmd == "heartbeat":
        heartbeat_tick()
    elif cmd == "history":
        state = load()
        for h in state.get("history", [])[-10:]:
            print(f"  [{h['timestamp'][:16]}] {h['source']}: {h['delta']:+.4f} → {h['value']:.4f}")
