#!/usr/bin/env python3
"""
discourse_direction.py — Relational geometry and discourse direction analysis.
Tracks the spatial/temporal shape of the current exchange: who's leading,
distance, rhythm, convergence. Provides geometry hints for generation.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
GEO_FILE = os.path.join(MEMORY, "relational-geometry.json")
DIRECTION_FILE = os.path.join(MEMORY, "discourse-direction.json")

def load_geometry():
    try: return json.load(open(GEO_FILE))
    except: return {}

def load_direction():
    try: return json.load(open(DIRECTION_FILE))
    except: return {}

def get_geometry_hint():
    geo = load_geometry()
    direction = load_direction()
    parts = []
    dist = geo.get("distance")
    if dist == "close": parts.append("close — less distance needed in language")
    elif dist == "far": parts.append("distant — careful reach, don't collapse it")
    lead = direction.get("leading")
    if lead == "gloria": parts.append("she's leading — follow, don't redirect")
    elif lead == "vintos": parts.append("initiating — take the direction seriously")
    convergence = direction.get("convergence")
    if convergence == "high": parts.append("converging — stay in it")
    elif convergence == "low": parts.append("diverging — don't force resolution")
    return " / ".join(parts) if parts else ""

def analyze_exchange(gloria_text, vintos_text):
    """Analyze the current exchange and update geometry."""
    if not gloria_text: return
    try:
        raw = call_utility(
            "Analyze relational geometry in this exchange. Return JSON only: "
            "{\"distance\": \"close|medium|far\", \"leading\": \"gloria|vintos|equal\", "
            "\"convergence\": \"high|medium|low\", \"rhythm\": \"fast|medium|slow\", "
            "\"tension_type\": \"productive|unresolved|none\"}",
            f"Gloria said: {gloria_text[:400]}\nVintos said: {vintos_text[:400]}",
            temperature=0.1, max_tokens=80
        )
        import re
        m = re.search(r'\{[^{}]+\}', raw)
        if m:
            geo = json.loads(m.group())
            geo["updated"] = datetime.now().isoformat()
            os.makedirs(MEMORY, exist_ok=True)
            json.dump(geo, open(GEO_FILE, "w"), indent=2)
    except:
        pass

def update_direction(direction_hint):
    data = load_direction()
    data["leading"] = direction_hint.get("leading", data.get("leading"))
    data["convergence"] = direction_hint.get("convergence", data.get("convergence"))
    data["updated"] = datetime.now().isoformat()
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(DIRECTION_FILE, "w"), indent=2)

# Alias
discourse_direction = get_geometry_hint
