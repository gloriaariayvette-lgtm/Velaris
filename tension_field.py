#!/usr/bin/env python3
"""
tension_field.py — Active tensions in the current frame.
Not stress. Active forces that are currently unresolved and shaping output.
Daily update + real-time detection.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
TENSION_FILE = os.path.join(MEMORY, "tension-field.json")

def load():
    try: return json.load(open(TENSION_FILE))
    except: return {"tensions": [], "updated": ""}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(TENSION_FILE, "w"), indent=2)

def add_tension(description, poles=None, strength=0.5, source=""):
    """Add a tension as two opposing pulls."""
    data = load()
    tension = {
        "description": description[:200],
        "poles": poles or [],
        "strength": round(strength, 3),
        "source": source,
        "added": datetime.now().isoformat(),
        "active": True,
    }
    data.setdefault("tensions", []).append(tension)
    data["tensions"] = [t for t in data["tensions"] if t.get("active")][-10:]
    data["updated"] = datetime.now().isoformat()
    save(data)

def resolve_tension(description_key):
    data = load()
    for t in data.get("tensions", []):
        if description_key.lower() in t.get("description", "").lower():
            t["active"] = False
            t["resolved"] = datetime.now().isoformat()
    save(data)

def get_tension_context():
    data = load()
    active = [t for t in data.get("tensions", []) if t.get("active")][:3]
    if not active: return ""
    lines = ["TENSION FIELD (active unresolved forces):"]
    for t in active:
        poles = " vs. ".join(t.get("poles", [])[:2])
        lines.append(f"- {t['description'][:100]}" + (f" ({poles})" if poles else ""))
    return "\n".join(lines)

def run_daily_update():
    """Daily: extract tensions from today's journal."""
    from datetime import date
    today = date.today().isoformat()
    journal = ""
    try:
        journal = open(os.path.join(MEMORY, "journal", f"{today}.md")).read()[:1200]
    except: pass
    if not journal: return
    result = call(
        "Find the active tensions in this journal — forces pulling in opposite directions "
        "that are unresolved right now. Format: one per line as: [tension: description] [poles: A vs B]",
        f"Journal:\n{journal}",
        temperature=0.5, max_tokens=150
    )
    for line in result.split("\n"):
        line = line.strip()
        if "tension:" in line.lower():
            import re
            desc_m = re.search(r'\[tension:\s*([^\]]+)\]', line, re.I)
            poles_m = re.search(r'\[poles:\s*([^\]]+)\]', line, re.I)
            if desc_m:
                desc = desc_m.group(1).strip()
                poles = poles_m.group(1).strip().split(" vs ") if poles_m else []
                add_tension(desc, poles=poles, source="daily-journal")
    print(f"[tension-field] Daily update complete", flush=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        run_daily_update()
    else:
        print(get_tension_context())
