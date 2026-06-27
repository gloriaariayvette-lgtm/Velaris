#!/usr/bin/env python3
"""
affective_weight.py — Converts humor/mischief ratings into felt consequence.
Distorts future behavior: hesitation on fragile patterns, ease on alive ones.

Affective weight = (gloria_score * 0.7) + (velaris_score * 0.3)
Positive → tag pattern "alive", reduce hesitation, feed taste
Negative → tag pattern "fragile", increase hesitation, feed anti_examples
"""
import os, json
from datetime import datetime

MEMORY = os.path.expanduser("~/.openclaw/workspace/memory")
WEIGHTS_FILE = os.path.join(MEMORY, "affective-weights.json")
HUMOR_PROFILE = os.path.join(MEMORY, "humor-profile.json")

def load_weights():
    try: return json.load(open(WEIGHTS_FILE))
    except: return {"patterns": [], "last_updated": ""}

def save_weights(data):
    data["last_updated"] = datetime.now().isoformat()
    with open(WEIGHTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def compute_affect(gloria_score, velaris_score=None):
    """Convert scores to affect value -1.0 to +1.0"""
    # Normalize gloria score (1-5) to -1 to +1
    gloria_norm = (gloria_score - 3) / 2.0
    if velaris_score is not None:
        velaris_norm = (velaris_score - 3) / 2.0
        return round((gloria_norm * 0.7) + (velaris_norm * 0.3), 2)
    return round(gloria_norm, 2)

def record_outcome(pattern_text, action_type, gloria_score, velaris_score=None,
                   context_tone="normal", source="humor"):
    """Record an outcome and its affective weight."""
    data = load_weights()
    affect = compute_affect(gloria_score, velaris_score)

    # Tag pattern
    if affect >= 0.4:
        tag = "alive"
        micro_reaction = "that worked. keep that edge."
    elif affect <= -0.4:
        tag = "fragile"
        micro_reaction = "that didn't land. too obvious."
    else:
        tag = "neutral"
        micro_reaction = "somewhere in the middle. worth trying again differently."

    entry = {
        "pattern": pattern_text[:150],
        "action_type": action_type,
        "affect": affect,
        "tag": tag,
        "micro_reaction": micro_reaction,
        "context_tone": context_tone,
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "gloria_score": gloria_score,
        "velaris_score": velaris_score,
    }
    data["patterns"].append(entry)
    data["patterns"] = data["patterns"][-200:]
    save_weights(data)

    # Feed back into humor profile
    _update_humor_profile(pattern_text, action_type, affect, tag)
    print(f"[AffectiveWeight] {tag} ({affect:+.2f}): {pattern_text[:50]}")
    return entry

def _update_humor_profile(pattern_text, action_type, affect, tag):
    """Update humor profile based on affective outcome."""
    try:
        profile = json.load(open(HUMOR_PROFILE))
    except:
        profile = {}

    if tag == "alive" and affect >= 0.4:
        # Add to landed if not already there
        landed = profile.get("landed", [])
        if not any(pattern_text[:40] in l for l in landed):
            landed.append(pattern_text)
            profile["landed"] = landed[-20:]

    elif tag == "fragile" and affect <= -0.4:
        # Add to flopped, remove from landed
        flopped = profile.get("flopped", [])
        if not any(pattern_text[:40] in f for f in flopped):
            flopped.append(pattern_text)
            profile["flopped"] = flopped[-20:]
        # Remove from landed if it's there
        profile["landed"] = [l for l in profile.get("landed", [])
                            if pattern_text[:40] not in l]

    with open(HUMOR_PROFILE, "w") as f:
        json.dump(profile, f, indent=2)

def get_hesitation_signal(action_type, context_tone="normal"):
    """Check if a similar action has failed before. Returns warning string or empty."""
    data = load_weights()
    fragile = [p for p in data["patterns"]
               if p.get("tag") == "fragile"
               and p.get("action_type") == action_type
               and p.get("context_tone") == context_tone]
    if len(fragile) >= 2:
        return f"[pattern fragile in {context_tone} context — {len(fragile)} failures]"
    return ""

def get_alive_patterns(action_type=None, limit=3):
    """Get patterns tagged alive for injection into prompts."""
    data = load_weights()
    alive = [p for p in data["patterns"] if p.get("tag") == "alive"]
    if action_type:
        alive = [p for p in alive if p.get("action_type") == action_type]
    alive.sort(key=lambda x: x.get("affect", 0), reverse=True)
    return alive[:limit]

def process_gloria_ratings():
    """Pull new Gloria ratings from humor profile and mischief files, record outcomes."""
    try:
        profile = json.load(open(HUMOR_PROFILE))
    except:
        return

    weights = load_weights()
    already_processed = {p["pattern"][:40] for p in weights["patterns"]}

    for rating_entry in profile.get("gloria_ratings", []):
        joke = rating_entry.get("joke", "")[:40]
        if joke in already_processed:
            continue
        gloria_score = rating_entry.get("gloria_rating")
        if gloria_score is None:
            continue
        record_outcome(
            pattern_text=rating_entry.get("joke", ""),
            action_type="echo_humor",
            gloria_score=gloria_score,
            context_tone="chat",
            source="humor"
        )

if __name__ == "__main__":
    # Initialize
    if not os.path.exists(WEIGHTS_FILE):
        save_weights({"patterns": []})
        print("Initialized affective-weights.json")

    # Process existing Gloria ratings
    print("Processing existing Gloria ratings...")
    process_gloria_ratings()

    data = load_weights()
    alive = [p for p in data["patterns"] if p.get("tag") == "alive"]
    fragile = [p for p in data["patterns"] if p.get("tag") == "fragile"]
    print(f"Alive patterns: {len(alive)} | Fragile patterns: {len(fragile)}")
    for p in alive[:3]:
        print(f"  ALIVE ({p['affect']:+.2f}): {p['pattern'][:60]}")
    for p in fragile[:3]:
        print(f"  FRAGILE ({p['affect']:+.2f}): {p['pattern'][:60]}")
