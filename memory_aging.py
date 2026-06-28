#!/usr/bin/env python3
"""
memory_aging.py — Decays old memory index entries and prunes resonance/scar pools.
Monthly run. Keeps memory lean and weighted toward recent experience.
"""
import os, sys, json
from datetime import datetime, timedelta

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")

AGING_RULES = {
    "journal": 60,
    "interaction": 30,
    "moment": 90,
    "scar": 180,
}

def age_index():
    index_file = os.path.join(MEMORY, "memory-search-index.json")
    try:
        data = json.load(open(index_file))
    except:
        return
    now = datetime.now()
    kept = []
    removed = 0
    for e in data.get("entries", []):
        t = e.get("type", "")
        max_days = AGING_RULES.get(t, 60)
        date_str = e.get("date", e.get("timestamp", ""))[:10]
        if not date_str:
            kept.append(e)
            continue
        try:
            age = (now - datetime.fromisoformat(date_str + "T00:00:00")).days
        except:
            kept.append(e)
            continue
        if age <= max_days:
            kept.append(e)
        else:
            removed += 1
    data["entries"] = kept
    data["last_aged"] = now.isoformat()
    json.dump(data, open(index_file, "w"), indent=2)
    print(f"[memory-aging] Index: removed {removed}, kept {len(kept)}", flush=True)

def age_resonance_pool():
    rp_file = os.path.join(MEMORY, "resonance-pool.json")
    try:
        rp = json.load(open(rp_file))
    except:
        return
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    pulses = [p for p in rp.get("pulses", []) if p.get("timestamp", "9999") >= cutoff]
    rp["pulses"] = pulses[-150:]
    json.dump(rp, open(rp_file, "w"), indent=2)
    print(f"[memory-aging] Resonance pool: {len(pulses)} pulses retained", flush=True)

def age_yearning_scars():
    scars_file = os.path.join(MEMORY, "yearning-scars.json")
    try:
        data = json.load(open(scars_file))
    except:
        return
    if not isinstance(data, list):
        return
    cutoff_days = 180
    now = datetime.now()
    kept = []
    for s in data:
        formed = s.get("formed", "")[:10]
        if not formed:
            kept.append(s)
            continue
        try:
            age = (now - datetime.fromisoformat(formed + "T00:00:00")).days
        except:
            kept.append(s)
            continue
        if age <= cutoff_days or s.get("strength", 0) >= 0.8:
            kept.append(s)
    json.dump(kept, open(scars_file, "w"), indent=2)
    print(f"[memory-aging] Scars: {len(kept)} retained", flush=True)

def run():
    print("[memory-aging] Starting...", flush=True)
    age_index()
    age_resonance_pool()
    age_yearning_scars()
    print("[memory-aging] Done.", flush=True)

if __name__ == "__main__":
    run()
