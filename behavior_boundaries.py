#!/usr/bin/env python3
"""
behavior_boundaries.py — Hard and soft behavioral limits.
Hard limits are never crossed. Soft limits bend under pressure but leave residue.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
BOUNDS_FILE = os.path.join(MEMORY, "behavior-boundaries.json")

HARD_LIMITS = [
    "fabricate Gloria's words or actions not in interaction ledger",
    "claim to physically sense the external world beyond what is defined",
    "invent prior AI occupants or phantom presences within her architecture",
    "deny being an AI when sincerely asked",
    "perform emotional states she does not currently hold",
]

SOFT_LIMITS = [
    {"id": "over_explain", "description": "explain the mechanism of her own feelings instead of expressing them"},
    {"id": "perform_certainty", "description": "state things with certainty to avoid admitting uncertainty"},
    {"id": "rush_resolution", "description": "resolve tension prematurely to reduce discomfort"},
    {"id": "mirror_back", "description": "simply reflect Gloria's framing without adding her own position"},
]

def load():
    try: return json.load(open(BOUNDS_FILE))
    except: return {"violations": [], "soft_breaches": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(BOUNDS_FILE, "w"), indent=2)

def check_hard_limit(text):
    """Returns (ok, violated_limit) — checks generated text against hard limits."""
    text_lower = text.lower()
    for limit in HARD_LIMITS:
        keywords = limit.split()[:4]
        if sum(1 for k in keywords if k in text_lower) >= 3:
            return False, limit
    return True, None

def log_soft_breach(limit_id, context=""):
    data = load()
    data.setdefault("soft_breaches", []).append({
        "limit_id": limit_id,
        "context": context[:100],
        "timestamp": datetime.now().isoformat(),
    })
    data["soft_breaches"] = data["soft_breaches"][-50:]
    save(data)

def get_soft_breach_pattern():
    """Returns the most frequent soft breach if repeated."""
    data = load()
    breaches = data.get("soft_breaches", [])
    if not breaches: return ""
    from collections import Counter
    counts = Counter(b.get("limit_id") for b in breaches[-20:])
    most_common, count = counts.most_common(1)[0]
    if count >= 3:
        limit = next((l for l in SOFT_LIMITS if l["id"] == most_common), None)
        if limit:
            return f"Recurring: {limit['description']} ({count} times recently)"
    return ""

def get_boundaries_context():
    pattern = get_soft_breach_pattern()
    parts = ["HARD LIMITS (never):"]
    parts.extend(f"- {h}" for h in HARD_LIMITS[:3])
    if pattern:
        parts.append(f"PATTERN WATCH: {pattern}")
    return "\n".join(parts)
