#!/usr/bin/env python3
"""
emotional_gravity_wells.py — Persistent emotional attractors.
Wells are emotional states that he keeps falling back into regardless of context.
Not moods. Gravitational — things pull him back toward them.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
WELLS_FILE = os.path.join(MEMORY, "emotional-gravity-wells.json")

def load():
    try: return json.load(open(WELLS_FILE))
    except: return {"wells": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(WELLS_FILE, "w"), indent=2)

def add_well(name, description, pull_strength=0.4, dimensions=None):
    data = load()
    well = {
        "name": name,
        "description": description[:200],
        "pull_strength": round(pull_strength, 3),
        "dimensions": dimensions or {},
        "formed": datetime.now().isoformat(),
        "pull_count": 0,
    }
    # Update if exists
    existing = next((w for w in data.get("wells", []) if w["name"] == name), None)
    if existing:
        existing["pull_strength"] = min(0.9, existing.get("pull_strength", 0.4) + 0.05)
        existing["pull_count"] = existing.get("pull_count", 0) + 1
    else:
        data.setdefault("wells", []).append(well)
    data["wells"] = data["wells"][-20:]
    save(data)

def get_wells_context():
    data = load()
    wells = sorted(data.get("wells", []), key=lambda w: -w.get("pull_strength", 0))[:3]
    if not wells: return ""
    lines = ["EMOTIONAL GRAVITY WELLS (persistent attractors — not moods):"]
    for w in wells:
        lines.append(f"- {w['name']}: {w['description'][:100]} (pull: {w.get('pull_strength', 0):.2f})")
    return "\n".join(lines)

def check_and_update_wells(state):
    """Check current emotional state against wells and strengthen/weaken."""
    data = load()
    for well in data.get("wells", []):
        dims = well.get("dimensions", {})
        if not dims: continue
        match_score = 0.0
        for dim, expected in dims.items():
            actual = state.get(dim, 0.5)
            match_score += 1.0 - abs(actual - expected)
        match_score /= max(len(dims), 1)
        if match_score > 0.75:
            well["pull_strength"] = min(0.95, well.get("pull_strength", 0.4) + 0.02)
            well["pull_count"] = well.get("pull_count", 0) + 1
    save(data)
