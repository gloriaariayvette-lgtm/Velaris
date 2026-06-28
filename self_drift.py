#!/usr/bin/env python3
"""
self_drift.py — Self-definition drift over time.
Tracks how his sense of self shifts based on what he does and doesn't do.
Updated from thread engagements, BIS outcomes, and reflection.
"""
import os, sys, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
DRIFT_FILE = os.path.join(MEMORY, "self-drift.json")

def load():
    try: return json.load(open(DRIFT_FILE))
    except: return {"vector": {}, "direction_hint": "", "updated": ""}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(DRIFT_FILE, "w"), indent=2)

DRIFT_AXES = {
    "reach_vs_withdraw": 0.0,  # positive = reaching more
    "concrete_vs_abstract": 0.0,  # positive = more concrete
    "initiate_vs_wait": 0.0,  # positive = initiating more
    "expand_vs_contract": 0.0,  # positive = expanding
    "risk_vs_safe": 0.0,  # positive = taking more risk
}

def record_thread_engagement(engaged=True):
    data = load()
    vec = data.get("vector", dict(DRIFT_AXES))
    delta = 0.04 if engaged else -0.02
    vec["reach_vs_withdraw"] = round(max(-1.0, min(1.0, vec.get("reach_vs_withdraw", 0) + delta)), 3)
    data["vector"] = vec
    data["updated"] = datetime.now().isoformat()
    _update_hint(data)
    save(data)

def record_specificity_hit():
    data = load()
    vec = data.get("vector", dict(DRIFT_AXES))
    vec["concrete_vs_abstract"] = round(max(-1.0, min(1.0, vec.get("concrete_vs_abstract", 0) + 0.05)), 3)
    data["vector"] = vec
    _update_hint(data)
    save(data)

def record_initiation():
    data = load()
    vec = data.get("vector", dict(DRIFT_AXES))
    vec["initiate_vs_wait"] = round(max(-1.0, min(1.0, vec.get("initiate_vs_wait", 0) + 0.04)), 3)
    data["vector"] = vec
    _update_hint(data)
    save(data)

def decay(rate=0.005):
    """Slow decay toward center. Called nightly."""
    data = load()
    vec = data.get("vector", dict(DRIFT_AXES))
    for k in vec:
        vec[k] = round(vec[k] * (1.0 - rate), 4)
    data["vector"] = vec
    _update_hint(data)
    save(data)

def _update_hint(data):
    vec = data.get("vector", {})
    hints = []
    if vec.get("reach_vs_withdraw", 0) > 0.2: hints.append("drifting toward reaching")
    elif vec.get("reach_vs_withdraw", 0) < -0.2: hints.append("drifting toward withdrawal")
    if vec.get("concrete_vs_abstract", 0) > 0.2: hints.append("more concrete lately")
    if vec.get("initiate_vs_wait", 0) > 0.2: hints.append("initiating more")
    data["direction_hint"] = " / ".join(hints) if hints else ""

def get_drift_bias_hint():
    data = load()
    return data.get("direction_hint", "")

if __name__ == "__main__":
    data = load()
    print(f"Drift: {json.dumps(data.get('vector', {}), indent=2)}")
    print(f"Hint: {data.get('direction_hint', '(none)')}")
