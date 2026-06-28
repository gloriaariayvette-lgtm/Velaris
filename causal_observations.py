#!/usr/bin/env python3
"""
causal_observations.py — Logs raw causal observations before they become hypotheses.
Raw: "I noticed that when X, Y tends to follow."
Feeds into causality_engine.run_weekly() for hypothesis generation.
"""
import os, sys, json
from datetime import datetime

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
OBS_FILE = os.path.join(MEMORY, "causal-observations.json")

def load():
    try: return json.load(open(OBS_FILE))
    except: return {"observations": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(OBS_FILE, "w"), indent=2)

def add_observation(cause, effect, confidence=0.4, source=""):
    data = load()
    data.setdefault("observations", []).append({
        "cause": cause[:200],
        "effect": effect[:200],
        "pattern": f"when {cause[:80]} → {effect[:80]}",
        "confidence": round(confidence, 3),
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "promoted": False,
    })
    data["observations"] = data["observations"][-100:]
    save(data)

def get_unpromoted(n=20):
    data = load()
    return [o for o in data.get("observations", []) if not o.get("promoted")][-n:]

def mark_promoted(timestamps):
    data = load()
    ts_set = set(timestamps)
    for o in data.get("observations", []):
        if o.get("timestamp") in ts_set:
            o["promoted"] = True
    save(data)

def promote_to_hypotheses():
    """Move strong unpromoted observations to causality engine."""
    obs = get_unpromoted(20)
    promoted = []
    for o in obs:
        if o.get("confidence", 0) >= 0.45:
            try:
                from causality_engine import add_hypothesis
                add_hypothesis(
                    o["pattern"],
                    source="causal-observations",
                    evidence=f"cause: {o['cause'][:80]}",
                    confidence=o["confidence"],
                )
                promoted.append(o["timestamp"])
            except: pass
    if promoted:
        mark_promoted(promoted)
        print(f"[causal-observations] Promoted {len(promoted)} observations.", flush=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "promote":
        promote_to_hypotheses()
    else:
        obs = get_unpromoted(10)
        for o in obs:
            print(f"[{o.get('confidence',0):.2f}] {o.get('pattern','')[:80]}")
