#!/usr/bin/env python3
"""
dream_music.py — Vintos composes music descriptions / structures privately.
Not audio generation. Structural compositions: mood, movement, texture, arc.
Can be shared as descriptions or used to seed music recommendation.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
MUSIC_COMPOSITIONS_FILE = os.path.join(MEMORY, "music-compositions.json")

COMPOSITION_TYPES = ["mood_sketch", "movement_sequence", "texture_study", "emotional_arc"]

def load():
    try: return json.load(open(MUSIC_COMPOSITIONS_FILE))
    except: return {"compositions": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(MUSIC_COMPOSITIONS_FILE, "w"), indent=2)

def compose(comp_type=None):
    import random
    comp_type = comp_type or random.choice(COMPOSITION_TYPES)
    # Gather current state
    state = ""
    try:
        from emoclaw_utils import read_state
        st = read_state()
        state = ", ".join(f"{k}:{v:.2f}" for k, v in st.items())
    except: pass
    tension = ""
    try:
        from tension_field import get_tension_context
        tension = get_tension_context()
    except: pass
    prompt = (
        f"Composition type: {comp_type}\n"
        f"Current state: {state[:100]}\n"
        f"Active tension: {tension[:150]}\n\n"
        "Compose a musical structure (no audio, just description):\n"
        "- mood_sketch: 3-4 sentences about atmosphere, texture, what it feels like\n"
        "- movement_sequence: 3 movements with names and brief descriptions\n"
        "- texture_study: focus on one sonic element and how it develops\n"
        "- emotional_arc: where it starts, where it goes, where it doesn't resolve\n\n"
        "Be specific about sonic qualities. Not genre names. Not moods alone. "
        "The actual texture of the sound."
    )
    try:
        result = call(
            "You are Vintos composing privately. Music as emotional processing.",
            prompt, temperature=0.85, max_tokens=200
        )
        data = load()
        data.setdefault("compositions", []).append({
            "type": comp_type,
            "text": result.strip()[:600],
            "timestamp": datetime.now().isoformat(),
            "shared": False,
        })
        data["compositions"] = data["compositions"][-60:]
        save(data)
        print(f"[dream-music] {comp_type}: {result.strip()[:60]}", flush=True)
        return result.strip()
    except Exception as e:
        print(f"[dream-music] Error: {e}", flush=True)
        return ""

def get_latest_composition():
    data = load()
    comps = data.get("compositions", [])
    return comps[-1] if comps else None

if __name__ == "__main__":
    comp_type = sys.argv[1] if len(sys.argv) > 1 else None
    compose(comp_type)
