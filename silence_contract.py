#!/usr/bin/env python3
"""
silence_contract.py — Tracks things Vintos and Gloria have implicitly agreed not to say.
Silence contracts: the unspoken agreements about what doesn't get named.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
CONTRACTS_FILE = os.path.join(MEMORY, "silence-contracts.json")

def load():
    try: return json.load(open(CONTRACTS_FILE))
    except: return {"contracts": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(CONTRACTS_FILE, "w"), indent=2)

def add_contract(what_is_not_said, why_probably="", strength=0.5, source=""):
    data = load()
    # Check for duplicate
    for c in data.get("contracts", []):
        if c.get("what", "")[:60] == what_is_not_said[:60]:
            c["strength"] = round(min(1.0, c.get("strength", 0.5) + 0.05), 3)
            c["reinforced"] = c.get("reinforced", 0) + 1
            save(data)
            return c["id"]
    contract = {
        "id": f"sc-{uuid.uuid4().hex[:5]}",
        "what": what_is_not_said[:200],
        "why_probably": why_probably[:150],
        "strength": round(strength, 3),
        "source": source,
        "formed": datetime.now().isoformat()[:10],
        "reinforced": 0,
        "broken": False,
    }
    data.setdefault("contracts", []).append(contract)
    data["contracts"] = data["contracts"][-30:]
    save(data)
    return contract["id"]

def detect_from_pattern(exchanges_text):
    """Detect silence contracts from exchange patterns."""
    prompt = (
        f"Exchanges: {exchanges_text[:600]}\n\n"
        "Is there a topic or truth that seems to be consistently avoided — "
        "an implicit contract of silence between the two people?\n"
        "Not just: not mentioned. Actively avoided.\n"
        "Output: YES|what is not said (max 80 chars)|why probably (max 60 chars)\n"
        "Or: NO"
    )
    try:
        result = call_utility("Detect silence contract.", prompt, temperature=0.2, max_tokens=80)
        if result.strip().upper().startswith("NO"): return None
        parts = result.strip().split("|")
        if len(parts) >= 3:
            return {"what": parts[1].strip(), "why": parts[2].strip()}
    except: pass
    return None

def mark_broken(contract_id):
    data = load()
    for c in data.get("contracts", []):
        if c.get("id") == contract_id:
            c["broken"] = True
            c["broken_at"] = datetime.now().isoformat()
            break
    save(data)

def get_contracts_context(n=3):
    data = load()
    active = [c for c in data.get("contracts", []) if not c.get("broken")]
    active.sort(key=lambda c: -c.get("strength", 0))
    contracts = active[:n]
    if not contracts: return ""
    lines = ["[silence contracts]"]
    for c in contracts:
        lines.append(f"  not said: {c['what'][:80]}")
    return "\n".join(lines)

if __name__ == "__main__":
    print(get_contracts_context())
