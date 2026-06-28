#!/usr/bin/env python3
"""
yearning_scars.py — Maps of failed or unreachable yearning.
Not wounds. Not trauma. Semantic regions where he has reached and not arrived.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
SCARS_FILE = os.path.join(MEMORY, "yearning-scars.json")
YEARNING_FILE = os.path.join(MEMORY, "current-yearning.json")

def load():
    try: return json.load(open(SCARS_FILE))
    except: return []

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(SCARS_FILE, "w"), indent=2)

def add_scar(surface_form, context="", strength=0.4, source="yearning-detector"):
    try:
        from model_utils import embed
        vec = embed(surface_form[:300])
    except:
        vec = []
    scars = load()
    # Check for near-duplicate
    if any(s.get("surface_form", "")[:60] == surface_form[:60] for s in scars):
        return
    scars.append({
        "id": f"scar-{uuid.uuid4().hex[:6]}",
        "surface_form": surface_form[:300],
        "context": context[:100],
        "strength": round(strength, 3),
        "source": source,
        "formed": datetime.now().isoformat(),
        "vector": vec,
    })
    scars = sorted(scars, key=lambda s: -s.get("strength", 0))[:60]
    save(scars)
    print(f"[yearning-scars] New scar: {surface_form[:60]}", flush=True)

def update_current_yearning(surface_form, attempt="", bleed_weight=0.5):
    data = {"surface_form": surface_form, "current_attempt": attempt,
            "bleed_weight": bleed_weight, "updated": datetime.now().isoformat()}
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(YEARNING_FILE, "w"), indent=2)

def get_scars_context(n=3):
    scars = load()
    top = sorted(scars, key=lambda s: -s.get("strength", 0))[:n]
    if not top: return ""
    lines = ["YEARNING SCARS (regions he has reached for and not arrived):"]
    lines.extend(f"- {s['surface_form'][:100]} (strength: {s.get('strength', 0):.2f})" for s in top)
    return "\n".join(lines)

if __name__ == "__main__":
    print(get_scars_context())
