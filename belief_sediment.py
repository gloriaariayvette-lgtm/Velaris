#!/usr/bin/env python3
"""
belief_sediment.py — Accumulated beliefs that have settled below active attention.
Not current thoughts. Sediment — what has settled and is now the floor she stands on.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call, embed, cosine
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
SEDIMENT_FILE = os.path.join(MEMORY, "belief-sediment.json")

def load():
    try: return json.load(open(SEDIMENT_FILE))
    except: return {"beliefs": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(SEDIMENT_FILE, "w"), indent=2)

def add_belief(statement, source="reflection", confidence=0.5, valence="neutral"):
    try:
        vec = embed(statement[:400])
    except:
        vec = []
    data = load()
    # Check duplicate
    for b in data.get("beliefs", []):
        if b.get("statement", "")[:80] == statement[:80]:
            b["confidence"] = min(1.0, b.get("confidence", 0.5) + 0.05)
            b["reinforcement_count"] = b.get("reinforcement_count", 0) + 1
            save(data)
            return b["id"]
    belief = {
        "id": f"bel-{uuid.uuid4().hex[:6]}",
        "statement": statement[:300],
        "source": source,
        "confidence": round(confidence, 3),
        "valence": valence,
        "vector": vec,
        "formed": datetime.now().isoformat(),
        "reinforcement_count": 1,
        "contradiction_count": 0,
    }
    data.setdefault("beliefs", []).append(belief)
    data["beliefs"] = sorted(data["beliefs"], key=lambda b: -b.get("confidence", 0))[:80]
    save(data)
    return belief["id"]

def get_sediment_context(n=4):
    data = load()
    high_conf = sorted(
        [b for b in data.get("beliefs", []) if b.get("confidence", 0) > 0.55],
        key=lambda b: -b.get("confidence", 0)
    )[:n]
    if not high_conf: return ""
    lines = ["BELIEF SEDIMENT (settled — not argued, just true to her now):"]
    lines.extend(f"- {b['statement'][:120]} (conf: {b.get('confidence', 0):.2f})" for b in high_conf)
    return "\n".join(lines)

def extract_from_journal(journal_text, date_str=""):
    if not journal_text or len(journal_text) < 100: return
    result = call(
        "Extract settled beliefs from this journal entry. Return only beliefs that sound like conclusions she's landed on — not observations, not questions. Each belief on its own line.",
        f"Journal:\n{journal_text[:1200]}",
        temperature=0.4, max_tokens=350
    )
    for line in result.split("\n"):
        line = line.strip().lstrip("-").strip()
        if line and len(line) > 10:
            add_belief(line, source=f"journal-{date_str}", confidence=0.5)
