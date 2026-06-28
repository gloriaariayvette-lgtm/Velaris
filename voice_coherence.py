#!/usr/bin/env python3
"""
voice_coherence.py — Tracks and scores Vintos's voice consistency over time.
Voice = particular combination of rhythm, density, angle, resistance.
Deviation from voice is logged and used to recalibrate.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility, embed, cosine
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
VOICE_FILE = os.path.join(MEMORY, "voice-coherence.md")
VOICE_VECTORS_FILE = os.path.join(MEMORY, "voice-vectors.json")

VOICE_MARKERS = [
    "syntactic density",
    "tonal resistance",
    "image specificity",
    "deflection patterns",
    "humor register",
    "emotional directness",
]

def load_vectors():
    try: return json.load(open(VOICE_VECTORS_FILE))
    except: return {"samples": [], "baseline": None}

def save_vectors(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(VOICE_VECTORS_FILE, "w"), indent=2)

def score_voice(text):
    """Return a voice coherence score 0.0-1.0 vs. baseline."""
    data = load_vectors()
    baseline = data.get("baseline")
    if not baseline: return None
    vec = embed(text)
    if not vec: return None
    return round(cosine(baseline, vec), 3)

def append_voice_log(text, score=None, event=""):
    """Append to voice-coherence.md for review."""
    ts = datetime.now().isoformat()[:16]
    score_str = f" [{score:.3f}]" if score is not None else ""
    event_str = f" — {event}" if event else ""
    line = f"\n[{ts}]{score_str}{event_str}\n{text[:300]}\n"
    try:
        with open(VOICE_FILE, "a") as f:
            f.write(line)
    except: pass

def update_baseline(text):
    """Add a sample to voice baseline (calibration text)."""
    data = load_vectors()
    vec = embed(text)
    if not vec: return
    data.setdefault("samples", []).append(vec)
    data["samples"] = data["samples"][-30:]
    # Compute mean
    n = len(data["samples"][0])
    mean = [sum(s[i] for s in data["samples"]) / len(data["samples"]) for i in range(n)]
    mag = sum(x*x for x in mean) ** 0.5 or 1.0
    data["baseline"] = [x / mag for x in mean]
    save_vectors(data)

def analyze_voice_pattern():
    """Weekly: analyze voice coherence log for patterns."""
    try:
        log = open(VOICE_FILE).read()[-2000:]
    except:
        return ""
    prompt = (
        f"Voice coherence log:\n{log}\n\n"
        "What patterns of voice deviation appear? What's the voice drifting toward?\n"
        "One paragraph, specific. Don't summarize — characterize."
    )
    try:
        from model_utils import call
        return call("Analyze voice coherence patterns.", prompt, temperature=0.4, max_tokens=150)
    except: return ""

def check_and_log(text, event=""):
    score = score_voice(text)
    if score is not None and score < 0.60:
        append_voice_log(text, score=score, event=event or "low-coherence")
    return score

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        print(analyze_voice_pattern())
    elif len(sys.argv) > 1 and sys.argv[1] == "baseline":
        text = " ".join(sys.argv[2:])
        if text:
            update_baseline(text)
            print("Baseline updated.")
    else:
        text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
        if text:
            score = check_and_log(text)
            print(f"Voice score: {score}")
