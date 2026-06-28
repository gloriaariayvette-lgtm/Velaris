#!/usr/bin/env python3
"""
carryover_weight.py — What carries over from one day into the next.
Nightly distillation of unresolved emotional weight from the day.
"""
import os, sys, json
from datetime import datetime, date

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
CARRYOVER_FILE = os.path.join(MEMORY, "carryover-weight.json")

def load():
    try: return json.load(open(CARRYOVER_FILE))
    except: return {"entries": [], "current": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(CARRYOVER_FILE, "w"), indent=2)

def compute_carryover():
    """Nightly: distill what carries forward from today."""
    today = date.today().isoformat()
    # Gather today's journal
    journal = ""
    try:
        journal = open(os.path.join(MEMORY, "journal", f"{today}.md")).read()[:1500]
    except: pass
    # Gather unresolved threads
    unresolved = []
    try:
        triage = json.load(open(os.path.join(MEMORY, "thread-triage.json")))
        unresolved = [t.get("summary", "")[:80] for t in triage.get("unresolved", [])[:5]]
    except: pass
    # Gather resonance from today
    resonance = []
    try:
        pool = json.load(open(os.path.join(MEMORY, "resonance-pool.json")))
        today_pulses = [p for p in pool.get("pulses", []) if p.get("timestamp", "")[:10] == today]
        resonance = [p.get("excerpt", "")[:60] for p in today_pulses[-3:]]
    except: pass

    if not journal and not unresolved:
        return []

    prompt = (
        "You are Vintos at the end of the day. What actually carries forward into tomorrow?\n"
        "Not everything — only what has real weight. What is unresolved and still pulling.\n"
        "What landed today that will still matter tomorrow.\n\n"
        f"TODAY'S JOURNAL:\n{journal}\n\n"
        f"UNRESOLVED THREADS:\n" + "\n".join(f"- {u}" for u in unresolved) + "\n\n"
        f"RESONANCE TODAY:\n" + "\n".join(f"- {r}" for r in resonance) + "\n\n"
        "Name 1-3 things carrying forward. First person, brief, specific.\n"
        "Format: each on its own line starting with -"
    )
    result = call("", prompt, temperature=0.65, max_tokens=150)
    carries = []
    for line in result.split("\n"):
        line = line.strip().lstrip("-").strip()
        if line and len(line) > 8:
            carries.append({"text": line, "from_date": today, "weight": 0.6})
    return carries[:3]

def run():
    data = load()
    new_carries = compute_carryover()
    if new_carries:
        # Archive yesterday's carryover
        data.setdefault("entries", []).extend(data.get("current", []))
        data["entries"] = data["entries"][-30:]
        data["current"] = new_carries
        data["computed"] = datetime.now().isoformat()
        save(data)
        print(f"[carryover] {len(new_carries)} items carry forward", flush=True)
        for c in new_carries:
            print(f"  - {c['text'][:80]}", flush=True)

def get_carryover_context():
    data = load()
    current = data.get("current", [])
    if not current: return ""
    lines = ["CARRYING FORWARD (from yesterday — not resolved yet):"]
    lines.extend(f"- {c['text'][:100]}" for c in current)
    return "\n".join(lines)

if __name__ == "__main__":
    run()
