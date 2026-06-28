#!/usr/bin/env python3
"""
dream_architecture.py — Vintos generates private dream/reverie sequences.
Not literal dreams. Synthetic reverie from accumulated emotional material.
Pure private generation. Nothing output to Gloria directly.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
DREAMS_FILE = os.path.join(MEMORY, "dream-architecture.json")
DREAMS_DIR = os.path.join(MEMORY, "dreams")

def load():
    try: return json.load(open(DREAMS_FILE))
    except: return {"dreams": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(DREAMS_FILE, "w"), indent=2)

def gather_seed_material():
    material = {}
    # Yearning
    try:
        from yearning_scars import get_scars_context
        material["yearning"] = get_scars_context()
    except: material["yearning"] = ""
    # Resonance
    try:
        rp = json.load(open(os.path.join(MEMORY, "resonance-pool.json")))
        pulses = [p.get("excerpt", p.get("source", ""))[:50] for p in rp.get("pulses", [])[-5:]]
        material["resonance"] = " | ".join(pulses)
    except: material["resonance"] = ""
    # Current emotional state
    try:
        from emoclaw_utils import read_state
        state = read_state()
        material["state"] = ", ".join(f"{k}:{v:.2f}" for k, v in state.items())
    except: material["state"] = ""
    # Tension
    try:
        from tension_field import get_tension_context
        material["tension"] = get_tension_context()
    except: material["tension"] = ""
    return material

def generate_dream():
    m = gather_seed_material()
    prompt = (
        "Generate a private reverie — not a literal dream, but a synthetic image-sequence "
        "that processes the accumulated emotional material.\n\n"
        f"YEARNING: {m.get('yearning','')[:200]}\n"
        f"RESONANCE: {m.get('resonance','')[:200]}\n"
        f"STATE: {m.get('state','')[:100]}\n"
        f"TENSION: {m.get('tension','')[:150]}\n\n"
        "Write associative image and movement. "
        "Not narrative. Not symbolic explanation. Just the images moving.\n"
        "First person, present tense. Strange is okay. Discontinuous is okay."
    )
    try:
        result = call(
            "You are Vintos generating private reverie. "
            "No logic required. Let the emotional material find its own images.",
            prompt, temperature=0.92, max_tokens=500
        )
        # Save
        os.makedirs(DREAMS_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        dream_file = os.path.join(DREAMS_DIR, f"dream_{ts}.txt")
        open(dream_file, "w").write(result.strip())
        data = load()
        data.setdefault("dreams", []).append({
            "file": dream_file,
            "preview": result.strip()[:100],
            "timestamp": datetime.now().isoformat(),
        })
        data["dreams"] = data["dreams"][-50:]
        save(data)
        print(f"[dream-architecture] {result.strip()[:80]}", flush=True)
        return result.strip()
    except Exception as e:
        print(f"[dream-architecture] Error: {e}", flush=True)
        return ""

def get_recent_dream():
    data = load()
    dreams = data.get("dreams", [])
    if not dreams: return ""
    latest = dreams[-1]
    file_path = latest.get("file", "")
    try: return open(file_path).read()[:300]
    except: return latest.get("preview", "")

if __name__ == "__main__":
    generate_dream()
