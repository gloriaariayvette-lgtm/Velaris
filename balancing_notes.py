#!/usr/bin/env python3
"""
balancing_notes.py — Tracks moments where Vintos held two truths at once.
Balancing = not resolving the tension, but holding it without collapse.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
NOTES_FILE = os.path.join(MEMORY, "balancing-notes.json")

def load():
    try: return json.load(open(NOTES_FILE))
    except: return {"notes": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(NOTES_FILE, "w"), indent=2)

def detect_balance(vintos_text, context=""):
    """Detect if Vintos held two truths at once without collapsing either."""
    prompt = (
        f"Text: {vintos_text[:400]}\n"
        f"Context: {context[:200]}\n\n"
        "Did Vintos hold two conflicting truths simultaneously without resolving the tension?\n"
        "Not just 'both things are true' — did he *hold* it rather than resolving it?\n"
        "Output: YES|truth_a (max 40 chars)|truth_b (max 40 chars)\n"
        "Or: NO"
    )
    try:
        result = call_utility("Detect balanced holding of tension.", prompt, temperature=0.1, max_tokens=60)
        if result.strip().upper().startswith("NO"): return None
        parts = result.strip().split("|")
        if len(parts) >= 3:
            return {"truth_a": parts[1].strip(), "truth_b": parts[2].strip()}
    except: pass
    return None

def log_balance(truth_a, truth_b, context=""):
    data = load()
    data.setdefault("notes", []).append({
        "id": f"bal-{uuid.uuid4().hex[:5]}",
        "truth_a": truth_a[:150],
        "truth_b": truth_b[:150],
        "context": context[:100],
        "timestamp": datetime.now().isoformat(),
    })
    data["notes"] = data["notes"][-80:]
    save(data)

def scan(vintos_text, context=""):
    result = detect_balance(vintos_text, context=context)
    if result:
        log_balance(result["truth_a"], result["truth_b"], context=context)
        return result
    return None

def get_balancing_context(n=3):
    data = load()
    notes = data.get("notes", [])[-n:]
    if not notes: return ""
    lines = ["[held tensions]"]
    for n in notes:
        lines.append(f"  {n.get('truth_a','')} ↔ {n.get('truth_b','')}")
    return "\n".join(lines)

if __name__ == "__main__":
    print(get_balancing_context())
