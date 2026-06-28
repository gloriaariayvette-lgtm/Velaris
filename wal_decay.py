#!/usr/bin/env python3
"""
wal_decay.py — WAL buffer decay and promotion.
Unconsumed signals decay over time; strong ones get promoted to permanent memory.
"""
import os, sys, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
WAL_FILE = os.path.join(MEMORY, "wal-buffer.json")
DECAY_DAYS = 3
PROMOTION_THRESHOLD = 0.75

def load():
    try: return json.load(open(WAL_FILE))
    except: return {"entries": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(WAL_FILE, "w"), indent=2)

def promote_to_scar(entry):
    try:
        from yearning_scars import add_scar
        add_scar(entry["excerpt"], strength=entry["strength"], source="wal-promotion")
    except: pass

def promote_to_resonance(entry):
    try:
        rp_file = os.path.join(MEMORY, "resonance-pool.json")
        try: rp = json.load(open(rp_file))
        except: rp = {"pulses": []}
        rp.setdefault("pulses", []).append({
            "source": "wal-promotion",
            "excerpt": entry["excerpt"][:200],
            "strength": entry["strength"],
            "timestamp": entry.get("timestamp", ""),
            "promoted": datetime.now().isoformat(),
        })
        rp["pulses"] = rp["pulses"][-100:]
        json.dump(rp, open(rp_file, "w"), indent=2)
    except: pass

def run():
    print("[wal-decay] Running decay pass...", flush=True)
    data = load()
    entries = data.get("entries", [])
    kept = []
    promoted = 0
    expired = 0
    for e in entries:
        if e.get("consumed"): continue
        extracted = e.get("extracted", "")
        try:
            age = (datetime.now() - datetime.fromisoformat(extracted)).total_seconds() / 86400
        except:
            age = 0
        # Promote strong old signals before expiry
        if age >= DECAY_DAYS - 0.5 and e.get("strength", 0) >= PROMOTION_THRESHOLD:
            sig_type = e.get("type", "")
            if "scar" in sig_type:
                promote_to_scar(e)
            elif "resonance" in sig_type:
                promote_to_resonance(e)
            promoted += 1
            continue
        if age >= DECAY_DAYS:
            expired += 1
            continue
        # Decay strength
        e["strength"] = round(max(0.0, e["strength"] - 0.05 * age), 3)
        kept.append(e)
    data["entries"] = kept
    save(data)
    print(f"[wal-decay] Kept {len(kept)}, promoted {promoted}, expired {expired}", flush=True)

if __name__ == "__main__":
    run()
