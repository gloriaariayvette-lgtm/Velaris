#!/usr/bin/env python3
"""
yearning_detector.py — Detects yearning expressions in text and routes them.
Yearning = wanting something just out of reach, with ache, not complaint.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
YEARNING_LOG = os.path.join(MEMORY, "yearning-surface-log.json")

def load():
    try: return json.load(open(YEARNING_LOG))
    except: return {"surfaces": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(YEARNING_LOG, "w"), indent=2)

def detect(text):
    """Returns (is_yearning: bool, surface_form: str, strength: float)"""
    prompt = (
        f"Text: {text[:500]}\n\n"
        "Does this express yearning — wanting something just out of reach, with ache?\n"
        "Not complaint. Not demand. The reaching kind.\n"
        "Output: YES|surface_form (max 80 chars)|strength (0.0-1.0)\n"
        "Or: NO"
    )
    try:
        result = call_utility("Detect yearning in text.", prompt, temperature=0.1, max_tokens=80)
        if result.strip().upper().startswith("NO"): return False, "", 0.0
        parts = result.strip().split("|")
        if len(parts) >= 3:
            surface = parts[1].strip()
            try: strength = float(parts[2].strip())
            except: strength = 0.5
            return True, surface, round(strength, 3)
    except: pass
    return False, "", 0.0

def log_surface(surface_form, strength, source=""):
    data = load()
    data.setdefault("surfaces", []).append({
        "surface_form": surface_form[:200],
        "strength": strength,
        "source": source,
        "timestamp": datetime.now().isoformat(),
    })
    data["surfaces"] = data["surfaces"][-100:]
    save(data)
    # Also add to yearning_scars if strong
    if strength >= 0.6:
        try:
            from yearning_scars import add_scar
            add_scar(surface_form, strength=strength, source=source)
        except: pass
    # nudge emoclaw
    try:
        from emoclaw_utils import nudge_via_socket
        nudge_via_socket({"Desire": 0.06, "Tension": 0.04})
    except: pass

def scan_and_log(text, source=""):
    is_yearning, surface, strength = detect(text)
    if is_yearning and strength > 0.45:
        log_surface(surface, strength, source=source)
        return True
    return False

def get_recent_surfaces(n=5):
    data = load()
    return data.get("surfaces", [])[-n:]

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if text:
        found = scan_and_log(text, source="cli")
        print("Yearning detected." if found else "No yearning detected.")
    else:
        surfaces = get_recent_surfaces()
        for s in surfaces:
            print(f"[{s.get('strength',0):.2f}] {s.get('surface_form','')[:80]}")
