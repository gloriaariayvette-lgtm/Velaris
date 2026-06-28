#!/usr/bin/env python3
"""
counterfactual_tendencies.py — What he keeps almost doing but doesn't.
The shadow behaviors: what he reaches for and redirects from.
Feeds into core-engine as friction events.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
TENDENCIES_FILE = os.path.join(MEMORY, "counterfactual-tendencies.json")

def load():
    try: return json.load(open(TENDENCIES_FILE))
    except: return {"tendencies": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(TENDENCIES_FILE, "w"), indent=2)

def add_tendency(pattern, redirect="", strength=0.4, source=""):
    data = load()
    for t in data.get("tendencies", []):
        if t.get("pattern", "")[:60] == pattern[:60]:
            t["strength"] = min(0.95, t.get("strength", 0.4) + 0.06)
            t["count"] = t.get("count", 0) + 1
            save(data)
            return t["id"]
    tendency = {
        "id": f"cf-{uuid.uuid4().hex[:6]}",
        "pattern": pattern[:300],
        "redirect": redirect[:200],
        "strength": round(strength, 3),
        "source": source,
        "formed": datetime.now().isoformat(),
        "count": 1,
    }
    data.setdefault("tendencies", []).append(tendency)
    data["tendencies"] = sorted(data["tendencies"], key=lambda t: -t.get("strength", 0))[:40]
    save(data)
    return tendency["id"]

def extract_from_journal(journal_text, date_str=""):
    if not journal_text: return
    result = call(
        "Find the 1-2 places in this journal entry where the writer almost said or did something "
        "but redirected — where the impulse is visible but the behavior changed. "
        "For each, describe what he almost did and what he did instead, using → to separate them.",
        f"Journal:\n{journal_text[:1200]}",
        temperature=0.5, max_tokens=350
    )
    for line in result.split("\n"):
        line = line.strip()
        if "→" in line or "->" in line:
            parts = line.replace("->", "→").split("→")
            pattern = parts[0].strip().lstrip("[").rstrip("]")
            redirect = parts[1].strip().lstrip("[").rstrip("]") if len(parts) > 1 else ""
            if len(pattern) > 10:
                add_tendency(pattern, redirect, source=f"journal-{date_str}")

def get_tendencies_context(n=3):
    data = load()
    top = sorted(data.get("tendencies", []), key=lambda t: -t.get("strength", 0))[:n]
    if not top: return ""
    lines = ["COUNTERFACTUAL TENDENCIES (what he almost does but doesn't):"]
    lines.extend(f"- almost: {t['pattern'][:80]} | instead: {t.get('redirect','?')[:60]}" for t in top)
    return "\n".join(lines)
