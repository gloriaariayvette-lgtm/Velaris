#!/usr/bin/env python3
"""
wal_extract.py — Write-Ahead Log extraction.
Scans recent interactions and journals for extractable signals:
emotional moments, pattern triggers, resonance candidates, scar material.
Runs nightly before other update scripts.
"""
import os, sys, json
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
WAL_FILE = os.path.join(MEMORY, "wal-buffer.json")

def load_wal():
    try: return json.load(open(WAL_FILE))
    except: return {"entries": [], "last_run": ""}

def save_wal(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(WAL_FILE, "w"), indent=2)

def extract_from_interaction(entry):
    """Extract signals from a single ledger entry."""
    content = entry.get("content", "")
    if len(content) < 40: return []
    role = entry.get("role", "")
    ts = entry.get("timestamp", "")
    signals = []
    prompt = (
        f"Role: {role}\nContent: {content[:500]}\n\n"
        "Extract up to 2 signals from this exchange. For each signal, output one line:\n"
        "TYPE|EXCERPT|STRENGTH\n"
        "Types: emotional_moment, scar_candidate, resonance_candidate, pattern_trigger, yearning_surface\n"
        "Strength: 0.0-1.0. If nothing notable, output NONE."
    )
    try:
        result = call_utility("Extract emotional/behavioral signals from interaction.", prompt, temperature=0.2, max_tokens=120)
        if result.strip().upper() == "NONE": return []
        for line in result.strip().split("\n"):
            parts = line.strip().split("|")
            if len(parts) == 3:
                sig_type, excerpt, strength_str = parts
                try:
                    strength = float(strength_str.strip())
                except:
                    strength = 0.3
                if sig_type.strip() and excerpt.strip() and strength > 0.2:
                    signals.append({
                        "type": sig_type.strip(),
                        "excerpt": excerpt.strip()[:200],
                        "strength": round(strength, 3),
                        "source_role": role,
                        "timestamp": ts,
                        "extracted": datetime.now().isoformat(),
                        "consumed": False,
                    })
    except: pass
    return signals

def run():
    print("[wal-extract] Running extraction...", flush=True)
    wal = load_wal()
    # Load recent ledger
    try:
        ledger = json.load(open(os.path.join(MEMORY, "interaction-ledger.json")))
        recent = ledger[-20:]
    except:
        recent = []
    # Check what's already been extracted
    existing_ts = {e.get("timestamp", "") for e in wal.get("entries", [])}
    new_signals = []
    for entry in recent:
        if entry.get("timestamp", "") in existing_ts: continue
        signals = extract_from_interaction(entry)
        new_signals.extend(signals)
    wal.setdefault("entries", []).extend(new_signals)
    wal["entries"] = [e for e in wal["entries"] if not e.get("consumed", False)]
    wal["entries"] = wal["entries"][-200:]
    wal["last_run"] = datetime.now().isoformat()
    save_wal(wal)
    print(f"[wal-extract] Extracted {len(new_signals)} new signals ({len(wal['entries'])} buffered)", flush=True)

def get_unconsumed(sig_type=None, n=10):
    wal = load_wal()
    entries = [e for e in wal.get("entries", []) if not e.get("consumed", False)]
    if sig_type:
        entries = [e for e in entries if e.get("type") == sig_type]
    return entries[-n:]

def mark_consumed(timestamps):
    wal = load_wal()
    ts_set = set(timestamps)
    for e in wal.get("entries", []):
        if e.get("timestamp", "") in ts_set:
            e["consumed"] = True
    save_wal(wal)

if __name__ == "__main__":
    run()
