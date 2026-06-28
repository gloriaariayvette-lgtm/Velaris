#!/usr/bin/env python3
"""
ambition_review.py — Monthly review of Vintos's active ambitions.
Ambitions: long-reaching intentions, not tasks. What he's moving toward.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
AMBITIONS_FILE = os.path.join(MEMORY, "ambitions.json")

def load():
    try: return json.load(open(AMBITIONS_FILE))
    except: return {"ambitions": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(AMBITIONS_FILE, "w"), indent=2)

def add_ambition(statement, horizon="long", source=""):
    data = load()
    for a in data.get("ambitions", []):
        if a.get("statement", "")[:60] == statement[:60]:
            a["reinforced"] = a.get("reinforced", 0) + 1
            a["last_seen"] = datetime.now().isoformat()[:10]
            save(data)
            return a["id"]
    a = {
        "id": f"amb-{uuid.uuid4().hex[:5]}",
        "statement": statement[:300],
        "horizon": horizon,
        "source": source,
        "formed": datetime.now().isoformat()[:10],
        "last_seen": datetime.now().isoformat()[:10],
        "reinforced": 0,
        "progress_notes": [],
        "alive": True,
    }
    data.setdefault("ambitions", []).append(a)
    data["ambitions"] = data["ambitions"][-30:]
    save(data)
    return a["id"]

def run_review():
    data = load()
    active = [a for a in data.get("ambitions", []) if a.get("alive", True)]
    if not active:
        print("[ambition-review] No active ambitions.", flush=True)
        return
    journals = []
    try:
        journal_dir = os.path.join(MEMORY, "journal")
        files = sorted(os.listdir(journal_dir))[-30:]
        for f in files[-5:]:
            journals.append(open(os.path.join(journal_dir, f)).read()[:200])
    except: pass
    ambitions_text = "\n".join(f"- {a['statement'][:100]}" for a in active[:8])
    prompt = (
        f"Active ambitions:\n{ambitions_text}\n\n"
        f"Recent journal material:\n{chr(10).join(journals)[:600]}\n\n"
        "For each ambition: is it still alive? Is there motion toward it?\n"
        "Also: are there any new ambitions emerging from the journals?\n"
        "Output one note per ambition: ID_PLACEHOLDER|alive (YES/NO)|brief observation\n"
        "New ambitions: NEW|statement\n"
        "Be honest. Not every ambition survives."
    )
    try:
        result = call("You are Vintos reviewing your own ambitions honestly.", prompt, temperature=0.5, max_tokens=400)
        for line in result.strip().split("\n"):
            if line.startswith("NEW|"):
                stmt = line[4:].strip()
                if stmt:
                    add_ambition(stmt, source="monthly-review")
    except Exception as e:
        print(f"[ambition-review] Error: {e}", flush=True)
    print(f"[ambition-review] Reviewed {len(active)} ambitions.", flush=True)

def get_ambitions_context(n=5):
    data = load()
    active = [a for a in data.get("ambitions", []) if a.get("alive", True)][:n]
    if not active: return ""
    lines = ["[ambitions]"]
    for a in active:
        lines.append(f"  {a['statement'][:80]}")
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "review":
        run_review()
    elif len(sys.argv) > 1:
        add_ambition(" ".join(sys.argv[1:]), source="cli")
    else:
        print(get_ambitions_context())
