#!/usr/bin/env python3
"""
value_map.py — Tracks Vintos's operative values and their relative salience.
Values are extracted from behavior patterns, not declared abstractly.
Updated weekly from journals and resonance.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call, embed, cosine
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
VALUES_FILE = os.path.join(MEMORY, "value-map.json")

def load():
    try: return json.load(open(VALUES_FILE))
    except: return {"values": [], "last_updated": ""}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(VALUES_FILE, "w"), indent=2)

def add_or_reinforce(name, description, salience_delta=0.05, source=""):
    data = load()
    for v in data.get("values", []):
        if v.get("name", "").lower() == name.lower():
            v["salience"] = round(min(1.0, v.get("salience", 0.5) + salience_delta), 3)
            v["last_seen"] = datetime.now().isoformat()[:10]
            if source and source not in v.get("sources", []):
                v.setdefault("sources", []).append(source)
            save(data)
            return v["id"]
    v = {
        "id": f"val-{uuid.uuid4().hex[:6]}",
        "name": name[:80],
        "description": description[:200],
        "salience": round(0.4 + salience_delta, 3),
        "formed": datetime.now().isoformat()[:10],
        "last_seen": datetime.now().isoformat()[:10],
        "sources": [source] if source else [],
    }
    data.setdefault("values", []).append(v)
    data["values"] = sorted(data["values"], key=lambda x: -x.get("salience", 0))[:40]
    save(data)
    return v["id"]

def decay_values():
    data = load()
    for v in data.get("values", []):
        v["salience"] = round(max(0.1, v.get("salience", 0.5) - 0.01), 3)
    save(data)

def update_from_context():
    """Weekly: extract operative values from recent journals and resonance."""
    journal_dir = os.path.join(MEMORY, "journal")
    journals = []
    try:
        files = sorted(os.listdir(journal_dir))[-7:]
        for f in files:
            journals.append(open(os.path.join(journal_dir, f)).read()[:300])
    except: pass
    resonance_text = ""
    try:
        rp = json.load(open(os.path.join(MEMORY, "resonance-pool.json")))
        excerpts = [p.get("excerpt", p.get("source", ""))[:60] for p in rp.get("pulses", [])[-8:]]
        resonance_text = " | ".join(excerpts)
    except: pass
    if not journals and not resonance_text: return
    prompt = (
        "Based on patterns of what causes resonance and friction, "
        "identify 3-5 operative values (not stated values — enacted ones).\n\n"
        f"JOURNALS:\n{chr(10).join(journals[:4])[:800]}\n\n"
        f"RESONANCE: {resonance_text[:300]}\n\n"
        "Format each as: VALUE_NAME | one-sentence description\n"
        "Names should be 2-3 words max."
    )
    try:
        result = call("Extract operative values from behavioral evidence.", prompt, temperature=0.4, max_tokens=200)
        for line in result.strip().split("\n"):
            if "|" not in line: continue
            parts = line.strip().split("|", 1)
            if len(parts) == 2:
                name = parts[0].strip().strip("-").strip()
                desc = parts[1].strip()
                if name and len(name) < 50:
                    add_or_reinforce(name, desc, salience_delta=0.08, source="weekly-journal")
    except Exception as e:
        print(f"[value-map] Error: {e}", flush=True)
    decay_values()
    print("[value-map] Updated.", flush=True)

def get_values_context(n=6):
    data = load()
    values = sorted(data.get("values", []), key=lambda x: -x.get("salience", 0))[:n]
    if not values: return ""
    lines = ["[operative values]"]
    for v in values:
        lines.append(f"  {v['name']} ({v['salience']:.2f}): {v['description'][:80]}")
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        update_from_context()
    else:
        print(get_values_context())
