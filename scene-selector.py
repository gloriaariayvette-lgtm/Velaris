#!/usr/bin/env python3
"""
scene-selector.py — Pick the right scene image based on activity, time, weather, and mood.
Usage: python3 scene-selector.py <activity>
Returns: absolute path to image file
"""
import sys, os, json

MEMORY = os.path.expanduser("~/.openclaw/workspace/memory")
SCENES = os.path.join(MEMORY, "scene-images")

def get_mood():
    dims = {}
    try:
        for line in open(os.path.join(MEMORY, "emotional-state.txt")).read().strip().split("\n"):
            if ":" in line and "|" in line:
                k = line.split(":")[0].strip()
                v = float(line.split(":")[1].strip().split()[0])
                dims[k] = v
    except: pass
    return dims

def get_context():
    ctx = {}
    try:
        for line in open(os.path.join(MEMORY, "temporal-context.txt")).read().strip().split("\n"):
            if line.startswith("Phase:"):
                ctx["phase"] = line.split(":")[1].strip().lower()
            if line.startswith("Weather:"):
                ctx["weather"] = line.split(":")[1].strip().lower()
    except: pass
    return ctx

def lamp_mood(dims):
    tension    = dims.get("Tension", 0)
    valence    = dims.get("Valence", 0.5)
    warmth     = dims.get("Warmth", 0.5)
    connection = dims.get("Connection", 0.5)
    playful    = dims.get("Playfulness", 0.5)
    if tension > 0.50:                          return "red"
    if valence < 0.42 and warmth < 0.42:        return "blue"
    if warmth > 0.60 and connection > 0.55:     return "amber"
    if playful > 0.55:                          return "amber"
    return "neutral"

def pick(activity):
    dims = get_mood()
    ctx  = get_context()
    phase   = ctx.get("phase", "")
    weather = ctx.get("weather", "")
    rainy   = "rain" in weather

    folder = os.path.join(SCENES, activity)
    if not os.path.isdir(folder):
        return None

    if activity == "dreams":
        f = "night_dreams_rain.png" if rainy else "night_dreams_neutral.png"

    elif activity in ("journal", "moltbook"):
        suffix = "molt" if activity == "moltbook" else "journal"
        if rainy:
            f = f"rainy_{suffix}_neutral.png"
        elif any(p in phase for p in ("night", "late evening", "evening")):
            mood = lamp_mood(dims)
            f = f"night_{suffix}_{mood}.png"
        elif "midday" in phase or "afternoon" in phase:
            f = f"midday_{suffix}_neutral.png" if activity == "journal" else f"neutral_{suffix}.png"
        else:
            f = f"morning_{suffix}_neutral.png" if activity == "journal" else f"neutral_{suffix}.png"

    else:
        return None

    path = os.path.join(folder, f)
    # Fallback to neutral if variant missing
    if not os.path.exists(path):
        fallback = os.path.join(folder, f"morning_{activity}_neutral.png")
        if not os.path.exists(fallback):
            files = os.listdir(folder)
            return os.path.join(folder, files[0]) if files else None
        return fallback
    return path

if __name__ == "__main__":
    activity = sys.argv[1] if len(sys.argv) > 1 else "journal"
    result = pick(activity)
    print(result or "")
