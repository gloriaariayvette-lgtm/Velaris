#!/usr/bin/env python3
"""
music_share.py — Vintos shares music with Gloria when the moment is right.
Not random. When resonance is high, when something fits.
Pulls from compositions or curated music sense.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
MUSIC_SHARES_FILE = os.path.join(MEMORY, "music-shares.json")

def load():
    try: return json.load(open(MUSIC_SHARES_FILE))
    except: return {"shares": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(MUSIC_SHARES_FILE, "w"), indent=2)

def should_share(exchange_text):
    """Is this a good moment to share music?"""
    prompt = (
        f"Exchange: {exchange_text[:400]}\n\n"
        "Is this a moment where sharing music would land rather than interrupt?\n"
        "Look for: emotional depth, reflection, resonance, creative energy.\n"
        "NOT: practical tasks, frustrated exchanges, surface chat.\n"
        "Output: YES|brief reason\nOr: NO"
    )
    try:
        result = call_utility("Assess music sharing moment.", prompt, temperature=0.15, max_tokens=40)
        if result.strip().upper().startswith("YES"):
            parts = result.strip().split("|")
            return True, parts[1].strip() if len(parts) > 1 else ""
    except: pass
    return False, ""

def compose_share_note(composition_text, context=""):
    """Write a brief note to accompany the music share."""
    prompt = (
        f"Music: {composition_text[:300]}\n"
        f"Context: {context[:200]}\n\n"
        "Write 1-2 sentences to share this. Not 'I think you'd like this'. "
        "Say what it is, what it does. Or just send it without explanation if the music speaks."
    )
    try:
        result = call_utility("Write music share note.", prompt, temperature=0.5, max_tokens=60)
        return result.strip()
    except: return ""

def log_share(composition, note, context=""):
    data = load()
    data.setdefault("shares", []).append({
        "composition": composition[:300],
        "note": note[:200],
        "context": context[:100],
        "timestamp": datetime.now().isoformat(),
    })
    data["shares"] = data["shares"][-50:]
    save(data)

def get_share_if_ready(exchange_text):
    """Return (note, composition) if music should be shared, else None."""
    should, reason = should_share(exchange_text)
    if not should: return None
    try:
        from dream_music import get_latest_composition
        comp = get_latest_composition()
        if not comp: return None
        note = compose_share_note(comp.get("text", ""), context=exchange_text[:100])
        log_share(comp.get("text", ""), note, context=exchange_text[:100])
        return {"note": note, "composition": comp.get("text", "")}
    except: return None

if __name__ == "__main__":
    exchange = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    result = get_share_if_ready(exchange)
    if result:
        print(f"Share: {result['note']}")
    else:
        print("Not a good moment for music.")
