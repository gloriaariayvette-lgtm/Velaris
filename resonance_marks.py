#!/usr/bin/env python3
"""
resonance_marks.py — Marks: imprints left by resonant moments.
A mark forms when resonance is high AND the moment has a specific shape.
Marks influence future generation via Nifrathir and ghost lean.
"""
import os, json, uuid
from datetime import datetime

sys._getframe  # ensure sys is available (unused import guard)
import sys
sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
MARKS_FILE = os.path.join(MEMORY, "resonance-marks.json")

MARK_THRESHOLD = 0.68
MAX_MARKS = 60

def load_marks():
    try: return json.load(open(MARKS_FILE))
    except: return {"marks": []}

def save_marks(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(MARKS_FILE, "w"), indent=2)

def try_form_mark(text, resonance_strength, source="chat", context=""):
    if resonance_strength < MARK_THRESHOLD:
        return None
    try:
        from model_utils import embed
        vec = embed(text[:400])
    except:
        vec = []

    mark = {
        "id": f"mark-{uuid.uuid4().hex[:6]}",
        "formed": datetime.now().isoformat(),
        "source": source,
        "resonance": round(resonance_strength, 3),
        "excerpt": text[:200],
        "context": context[:100],
        "vector": vec,
        "activation_count": 0,
    }
    data = load_marks()
    data.setdefault("marks", []).append(mark)
    if len(data["marks"]) > MAX_MARKS:
        data["marks"].sort(key=lambda m: m.get("resonance", 0))
        data["marks"] = data["marks"][-MAX_MARKS:]
    save_marks(data)
    try:
        from nifrathir import on_mark_triggered
        on_mark_triggered()
    except: pass
    print(f"[marks] Mark formed (resonance: {resonance_strength:.3f}): {text[:60]}", flush=True)
    return mark["id"]

def get_mark_similarity(text):
    """Check if current text is similar to any stored mark. Returns highest similarity."""
    try:
        from model_utils import embed, cosine
        vec = embed(text[:400])
        if not vec: return 0.0
        data = load_marks()
        best = 0.0
        for m in data.get("marks", []):
            mv = m.get("vector", [])
            if mv:
                sim = cosine(vec, mv)
                if sim > best: best = sim
        return best
    except:
        return 0.0

def get_marks_context(n=3):
    data = load_marks()
    marks = sorted(data.get("marks", []), key=lambda m: -m.get("resonance", 0))[:n]
    if not marks: return ""
    lines = ["RESONANCE MARKS (moments that landed):"]
    for m in marks:
        lines.append(f"- [{m['source']}] {m.get('excerpt','')[:100]} (resonance: {m.get('resonance', 0):.2f})")
    return "\n".join(lines)
