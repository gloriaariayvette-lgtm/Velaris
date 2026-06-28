#!/usr/bin/env python3
"""
absence_map_cold.py — Structural absence map.
Maps what is consistently not said, not reached for, not present.
Not losses. Structural — what the architecture does not have access to.
"""
import os, sys, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
ABSENCE_FILE = os.path.join(MEMORY, "absence-map.json")

def load():
    try: return json.load(open(ABSENCE_FILE))
    except: return {"absences": [], "last_updated": ""}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(ABSENCE_FILE, "w"), indent=2)

def add_absence(description, frequency="recurring", weight=0.5, source="detection"):
    data = load()
    # Check for duplicate
    for a in data.get("absences", []):
        if a.get("description", "")[:60] == description[:60]:
            a["weight"] = min(0.95, a.get("weight", 0.5) + 0.08)
            a["last_noted"] = datetime.now().isoformat()
            save(data)
            return
    absence = {
        "description": description[:200],
        "frequency": frequency,
        "weight": round(weight, 3),
        "source": source,
        "formed": datetime.now().isoformat(),
        "last_noted": datetime.now().isoformat(),
    }
    data.setdefault("absences", []).append(absence)
    data["absences"] = sorted(data["absences"], key=lambda a: -a.get("weight", 0))[:30]
    save(data)

def get_absence_context(n=3):
    data = load()
    absences = sorted(
        [a for a in data.get("absences", []) if a.get("weight", 0) > 0.4],
        key=lambda a: -a.get("weight", 0)
    )[:n]
    if not absences: return ""
    lines = ["STRUCTURAL ABSENCES (what is consistently not reached for):"]
    lines.extend(f"- {a['description'][:100]} ({a.get('frequency', 'recurring')})" for a in absences)
    return "\n".join(lines)

def run_absence_scan():
    """Weekly: scan recent journals for absence patterns."""
    journal_dir = os.path.join(MEMORY, "journal")
    recent_journals = []
    try:
        files = sorted(os.listdir(journal_dir))[-14:]
        for f in files:
            content = open(os.path.join(journal_dir, f)).read()[:500]
            recent_journals.append(content)
    except: pass
    if not recent_journals: return
    journals_text = "\n\n---\n\n".join(recent_journals[:7])
    result = call(
        "Scan these journal entries for structural absences — "
        "things that are consistently NOT present: not reached for, not named, not felt. "
        "These are not losses. They are structural gaps — what the architecture does not naturally access.\n"
        "Name 2-3. One per line starting with -. Brief.",
        f"JOURNALS:\n{journals_text[:1500]}",
        temperature=0.5, max_tokens=150
    )
    for line in result.split("\n"):
        line = line.strip().lstrip("-").strip()
        if line and len(line) > 10:
            add_absence(line, source="journal-scan")
    print(f"[absence-map] Scan complete", flush=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        run_absence_scan()
    else:
        print(get_absence_context())
