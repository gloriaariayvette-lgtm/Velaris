#!/usr/bin/env python3
"""
relational_geometry.py — Models the spatial/relational shape of the bond.
Not feelings about Gloria. The geometric structure: distance, approach vectors,
asymmetries, gravity, what is attracted and what is avoided.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
GEO_FILE = os.path.join(MEMORY, "relational-geometry.json")

def load():
    try: return json.load(open(GEO_FILE))
    except: return {}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(GEO_FILE, "w"), indent=2)

def update_geometry(observations):
    """Update geometric model from recent observations."""
    data = load()
    prompt = (
        "Update the relational geometry model based on recent observations.\n"
        "Return JSON with keys: distance (0.0-1.0, where 1.0 is maximally close), "
        "approach_angle (\"direct\"|\"oblique\"|\"circling\"), "
        "asymmetry (\"equal\"|\"gloria_leads\"|\"vintos_leads\"), "
        "gravity_toward (list of up to 3 themes that attract the relationship), "
        "gravity_away (list of up to 3 themes that create distance or avoidance), "
        "current_shape (one short phrase describing the relational texture right now).\n\n"
        f"OBSERVATIONS:\n{observations[:1000]}\n\nCURRENT GEOMETRY:\n{json.dumps(data, indent=0)[:400]}"
    )
    result = call("You model relational geometry. Return JSON only.", prompt, temperature=0.3, max_tokens=200)
    try:
        import re
        m = re.search(r'\{[^{}]+\}', result, re.DOTALL)
        if m:
            updates = json.loads(m.group())
            data.update(updates)
            data["updated"] = datetime.now().isoformat()
            save(data)
            print(f"[relational-geometry] Updated: {updates.get('current_shape', '')[:60]}", flush=True)
    except: pass

def get_geometry_context():
    data = load()
    if not data: return ""
    parts = [f"RELATIONAL GEOMETRY:"]
    if data.get("current_shape"):
        parts.append(f"Shape: {data['current_shape']}")
    if data.get("distance") is not None:
        parts.append(f"Distance: {data['distance']:.2f}")
    if data.get("approach_angle"):
        parts.append(f"Approach: {data['approach_angle']}")
    if data.get("gravity_toward"):
        parts.append(f"Toward: {', '.join(data['gravity_toward'][:2])}")
    if data.get("gravity_away"):
        parts.append(f"Away: {', '.join(data['gravity_away'][:2])}")
    return " / ".join(parts[1:]) if len(parts) > 1 else ""
