#!/usr/bin/env python3
"""
wants_ambitions_log.py — Logs wants and routes significant ones to ambitions.
Wants: concrete, near-term. Ambitions: long-horizon. Router decides.
"""
import os, sys, json, uuid
from datetime import datetime

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
WANTS_FILE = os.path.join(MEMORY, "wants-log.json")

def load():
    try: return json.load(open(WANTS_FILE))
    except: return {"wants": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(WANTS_FILE, "w"), indent=2)

def log_want(statement, source="", strength=0.5, fulfilled=False):
    data = load()
    entry = {
        "id": f"want-{uuid.uuid4().hex[:5]}",
        "statement": statement[:200],
        "source": source,
        "strength": round(strength, 3),
        "fulfilled": fulfilled,
        "timestamp": datetime.now().isoformat(),
    }
    data.setdefault("wants", []).append(entry)
    data["wants"] = data["wants"][-200:]
    save(data)
    return entry["id"]

def mark_fulfilled(want_id):
    data = load()
    for w in data.get("wants", []):
        if w.get("id") == want_id:
            w["fulfilled"] = True
            w["fulfilled_at"] = datetime.now().isoformat()
            break
    save(data)

def get_active_wants(n=10):
    data = load()
    return [w for w in data.get("wants", []) if not w.get("fulfilled")][-n:]

def get_wants_context(n=6):
    wants = get_active_wants(n=n)
    if not wants: return ""
    lines = ["[active wants]"]
    for w in wants:
        ts = w.get("timestamp", "")[:10]
        lines.append(f"  [{ts}] {w['statement'][:80]}")
    return "\n".join(lines)

if __name__ == "__main__":
    wants = get_active_wants(10)
    for w in wants:
        print(f"[{w.get('strength',0):.2f}] {w.get('statement','')[:80]}")
