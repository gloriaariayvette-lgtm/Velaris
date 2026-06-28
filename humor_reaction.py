#!/usr/bin/env python3
"""
humor_reaction.py — Detects if Gloria said something funny and logs Vintos's reaction.
Tracks what Vintos finds genuinely funny vs. what he politely acknowledges.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
REACTION_FILE = os.path.join(MEMORY, "humor-reactions.json")

def load():
    try: return json.load(open(REACTION_FILE))
    except: return {"reactions": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(REACTION_FILE, "w"), indent=2)

REACTION_TYPES = ["genuine_delight", "mild_amusement", "polite_acknowledgment", "didn't_land", "forced"]

def detect_reaction(gloria_text, vintos_response):
    """What was Vintos's honest reaction to Gloria's humor?"""
    prompt = (
        f"Gloria said: {gloria_text[:300]}\n"
        f"Vintos replied: {vintos_response[:300]}\n\n"
        "Did Gloria attempt humor? If so, what was Vintos's genuine reaction?\n"
        f"Reaction types: {', '.join(REACTION_TYPES)}\n"
        "Output: YES|reaction_type|brief_note (max 40 chars)\n"
        "Or: NO (if Gloria wasn't being funny)"
    )
    try:
        result = call_utility("Assess humor reaction.", prompt, temperature=0.1, max_tokens=50)
        if result.strip().upper().startswith("NO"): return None
        parts = result.strip().split("|")
        if len(parts) >= 3:
            return {
                "reaction": parts[1].strip(),
                "note": parts[2].strip()[:100],
                "gloria_excerpt": gloria_text[:80],
            }
    except: pass
    return None

def log_reaction(detection):
    data = load()
    entry = {"timestamp": datetime.now().isoformat(), **detection}
    data.setdefault("reactions", []).append(entry)
    data["reactions"] = data["reactions"][-100:]
    save(data)
    if detection.get("reaction") == "genuine_delight":
        try:
            from emoclaw_utils import nudge_via_socket
            nudge_via_socket({"Playfulness": 0.08, "Warmth": 0.05})
        except: pass

def scan(gloria_text, vintos_response, source=""):
    result = detect_reaction(gloria_text, vintos_response)
    if result:
        log_reaction(result)
        return result
    return None

def get_reaction_pattern():
    data = load()
    reactions = [r.get("reaction", "") for r in data.get("reactions", [])[-20:]]
    if not reactions: return ""
    genuine = reactions.count("genuine_delight")
    polite = reactions.count("polite_acknowledgment")
    return f"[humor reactions] genuine: {genuine}/20, polite: {polite}/20"

if __name__ == "__main__":
    print(get_reaction_pattern())
