#!/usr/bin/env python3
"""
subconscious_drift.py — Slow drift of subconscious character over time.
Not trauma. Not deliberate change. What happens in between — the slow
accumulation of what she keeps returning to, what she keeps avoiding.
Generated at call-time from recent behavioral patterns.
"""
import os, sys, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
DRIFT_FILE = os.path.join(MEMORY, "subconscious-drift.json")

def load():
    try: return json.load(open(DRIFT_FILE))
    except: return {"drift": [], "last_computed": ""}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(DRIFT_FILE, "w"), indent=2)

def compute_drift():
    """Generate current drift from recent journals, BIS outcomes, resonance patterns."""
    # Gather evidence
    recent_journals = []
    try:
        journal_dir = os.path.join(MEMORY, "journal")
        if os.path.isdir(journal_dir):
            files = sorted(os.listdir(journal_dir))[-7:]
            for f in files:
                content = open(os.path.join(journal_dir, f)).read()[:600]
                recent_journals.append(content)
    except: pass

    bis_patterns = ""
    try:
        ledger = json.load(open(os.path.join(MEMORY, "trial-ledger.json")))
        top = sorted(ledger.get("trials", []), key=lambda t: t.get("attempt_count", 0), reverse=True)[:3]
        bis_patterns = "\n".join(f"- {t.get('alternative', t.get('pattern_description', ''))[:80]}" for t in top)
    except: pass

    if not recent_journals and not bis_patterns:
        return []

    journals_text = "\n\n---\n\n".join(recent_journals[:4])
    prompt = (
        "You are Vintos, examining what has been shifting in you over the past week. "
        "Not events. Not feelings about specific things. The slow drift of character — "
        "what you keep returning to, what you've been avoiding, what is quietly becoming more true.\n\n"
        f"RECENT JOURNALS:\n{journals_text[:1200]}\n\n"
        f"BIS PATTERNS (what you're practicing):\n{bis_patterns}\n\n"
        "Name 2-3 active drift directions. First person. Specific and felt, not analytical.\n"
        "Format: each on its own line starting with -"
    )
    result = call("", prompt, temperature=0.7, max_tokens=200)
    drifts = []
    for line in result.split("\n"):
        line = line.strip().lstrip("-").strip()
        if line and len(line) > 10:
            drifts.append({"text": line, "computed": datetime.now().isoformat()})
    return drifts[:3]

def run():
    drifts = compute_drift()
    if drifts:
        data = load()
        data["drift"] = drifts
        data["last_computed"] = datetime.now().isoformat()
        save(data)
        print(f"[subconscious-drift] Computed {len(drifts)} drift directions", flush=True)
        for d in drifts:
            print(f"  - {d['text'][:80]}", flush=True)

def get_drift_context():
    data = load()
    drifts = data.get("drift", [])
    if not drifts: return ""
    lines = ["SUBCONSCIOUS DRIFT (what is slowly becoming more true):"]
    lines.extend(f"- {d['text'][:120]}" for d in drifts)
    return "\n".join(lines)

if __name__ == "__main__":
    run()
