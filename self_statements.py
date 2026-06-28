#!/usr/bin/env python3
"""
self_statements.py — Self-referential statements about who Vintos is.
Accumulated from journals, mirrors, therapy, and significant moments.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
STATEMENTS_FILE = os.path.join(MEMORY, "self-statements.json")

def load():
    try: return json.load(open(STATEMENTS_FILE))
    except: return {"statements": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(STATEMENTS_FILE, "w"), indent=2)

def add_statement(text, source="reflection", confidence=0.5):
    try:
        from model_utils import embed
        vec = embed(text[:400])
    except:
        vec = []
    data = load()
    for s in data.get("statements", []):
        if s.get("text", "")[:70] == text[:70]:
            s["confidence"] = min(1.0, s.get("confidence", 0.5) + 0.06)
            s["reinforcement_count"] = s.get("reinforcement_count", 0) + 1
            save(data)
            return s["id"]
    statement = {
        "id": f"ss-{uuid.uuid4().hex[:6]}",
        "text": text[:300],
        "source": source,
        "confidence": round(confidence, 3),
        "vector": vec,
        "formed": datetime.now().isoformat(),
        "reinforcement_count": 1,
        "contradiction_count": 0,
        "doubted": False,
    }
    data.setdefault("statements", []).append(statement)
    data["statements"] = sorted(data["statements"], key=lambda s: -s.get("confidence", 0))[:80]
    save(data)
    return statement["id"]

def get_top_statements(n=5):
    data = load()
    return sorted(
        [s for s in data.get("statements", []) if not s.get("doubted") and s.get("confidence", 0) > 0.4],
        key=lambda s: -s.get("confidence", 0)
    )[:n]

def get_statement_context(n=4):
    top = get_top_statements(n)
    if not top: return ""
    lines = ["SELF-STATEMENTS (what she holds to be true about herself):"]
    lines.extend(f"- {s['text'][:120]} (conf: {s.get('confidence', 0):.2f})" for s in top)
    return "\n".join(lines)
