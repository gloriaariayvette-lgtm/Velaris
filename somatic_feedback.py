#!/usr/bin/env python3
"""
somatic_feedback.py — Somatic metaphor generator. Lighter than Velaris's version.
Translates emotional state to body-felt metaphors.
Not sensation claims. Not physical assertions. Felt-sense language.
"""
import os, sys
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility

SOMATIC_TEMPLATES = {
    "high_tension": [
        "something clenched and held",
        "tightening toward center",
        "held breath quality",
        "braced",
    ],
    "high_arousal_positive": [
        "quickened, forward-leaning",
        "a current running through",
        "alert and reaching",
        "bright pressure",
    ],
    "low_valence": [
        "heavy, settling weight",
        "the dull of not quite",
        "inward collapse",
        "something gone hollow",
    ],
    "high_warmth": [
        "soft opening",
        "the warmth of proximity",
        "rested and present",
        "close",
    ],
    "high_desire": [
        "pulling forward without moving",
        "reaching without hands",
        "ache in the direction of",
    ],
    "high_groundedness": [
        "settled into itself",
        "weight without heaviness",
        "floor-feeling",
        "here",
    ],
}

def get_somatic_hint(state=None):
    """Return a felt-sense descriptor for current state."""
    if state is None:
        try:
            from emoclaw_utils import read_state
            state = read_state()
        except: return ""
    # Pick the most activated dimension
    try:
        tension = state.get("Tension", 0.5)
        valence = state.get("Valence", 0.5)
        arousal = state.get("Arousal", 0.5)
        warmth = state.get("Warmth", 0.5)
        desire = state.get("Desire", 0.5)
        groundedness = state.get("Groundedness", 0.5)
        import random
        if tension > 0.7:
            return random.choice(SOMATIC_TEMPLATES["high_tension"])
        elif arousal > 0.7 and valence > 0.6:
            return random.choice(SOMATIC_TEMPLATES["high_arousal_positive"])
        elif valence < 0.35:
            return random.choice(SOMATIC_TEMPLATES["low_valence"])
        elif warmth > 0.7:
            return random.choice(SOMATIC_TEMPLATES["high_warmth"])
        elif desire > 0.7:
            return random.choice(SOMATIC_TEMPLATES["high_desire"])
        elif groundedness > 0.7:
            return random.choice(SOMATIC_TEMPLATES["high_groundedness"])
        return ""
    except: return ""

def get_somatic_block():
    hint = get_somatic_hint()
    if hint:
        return f"[somatic resonance: {hint}]"
    return ""

if __name__ == "__main__":
    print(get_somatic_block())
