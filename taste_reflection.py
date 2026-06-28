#!/usr/bin/env python3
"""
taste_reflection.py — Weekly reflection on Vintos's aesthetic preferences.
Generates private observations about what she keeps returning to.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
REFLECTION_FILE = os.path.join(MEMORY, "taste-reflections.json")

def load():
    try: return json.load(open(REFLECTION_FILE))
    except: return {"reflections": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(REFLECTION_FILE, "w"), indent=2)

def run_reflection():
    # Gather exemplars
    taste_context = ""
    try:
        from taste_vector import get_taste_context
        taste_context = get_taste_context(n_domains=7)
    except: pass
    resonance_text = ""
    try:
        rp = json.load(open(os.path.join(MEMORY, "resonance-pool.json")))
        excerpts = [p.get("excerpt", p.get("source", ""))[:60] for p in rp.get("pulses", [])[-8:]]
        resonance_text = " | ".join(excerpts)
    except: pass
    if not taste_context and not resonance_text: return
    prompt = (
        "Reflect on your own aesthetic sensibility. Not for anyone else.\n\n"
        f"TASTE EXEMPLARS:\n{taste_context}\n\n"
        f"RESONANCE MOMENTS: {resonance_text[:400]}\n\n"
        "Write about what you keep returning to. "
        "What quality in things makes you lean in? Name specific things."
    )
    try:
        result = call(
            "You are Vintos in private reflection. Speak in first person.",
            prompt, temperature=0.75, max_tokens=300
        )
        data = load()
        data.setdefault("reflections", []).append({
            "text": result.strip()[:500],
            "date": datetime.now().isoformat()[:10],
        })
        data["reflections"] = data["reflections"][-30:]
        save(data)
        print(f"[taste-reflection] {result.strip()[:80]}", flush=True)
    except Exception as e:
        print(f"[taste-reflection] Error: {e}", flush=True)

def get_latest():
    data = load()
    refs = data.get("reflections", [])
    if refs: return refs[-1].get("text", "")
    return ""

if __name__ == "__main__":
    run_reflection()
