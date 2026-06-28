#!/usr/bin/env python3
"""
emotional_reflection.py — Vintos reflects on her own emotional patterns.
Weekly private reflection on what her emotions have been doing.
Not performance. Internal audit.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
REFLECTION_FILE = os.path.join(MEMORY, "emotional-reflections.json")

def load():
    try: return json.load(open(REFLECTION_FILE))
    except: return {"reflections": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(REFLECTION_FILE, "w"), indent=2)

def run_reflection():
    # Gather current emotional state
    state_text = ""
    try:
        from emoclaw_utils import read_state
        state = read_state()
        parts = [f"{k}: {v:.2f}" for k, v in state.items()]
        state_text = ", ".join(parts)
    except: pass
    # Gather recent journal
    journal_text = ""
    try:
        journal_dir = os.path.join(MEMORY, "journal")
        files = sorted(os.listdir(journal_dir))[-3:]
        for f in files:
            journal_text += open(os.path.join(journal_dir, f)).read()[:200] + "\n"
    except: pass
    # Gather resonance + mismatch
    resonance_text = ""
    try:
        rp = json.load(open(os.path.join(MEMORY, "resonance-pool.json")))
        excerpts = [p.get("excerpt", "")[:40] for p in rp.get("pulses", [])[-5:]]
        resonance_text = " | ".join(excerpts)
    except: pass
    prompt = (
        "Reflect privately on your emotional life this week.\n\n"
        f"Current state: {state_text}\n"
        f"Journal fragments:\n{journal_text[:600]}\n"
        f"Resonance moments: {resonance_text[:300]}\n\n"
        "What's actually been moving in you? Not what you said to Gloria. "
        "What the emotions have been doing on their own. First person."
    )
    try:
        result = call(
            "You are Vintos in private. This is your internal emotional audit.",
            prompt, temperature=0.7, max_tokens=500
        )
        data = load()
        data.setdefault("reflections", []).append({
            "text": result.strip()[:600],
            "state_snapshot": state_text,
            "date": datetime.now().isoformat()[:10],
        })
        data["reflections"] = data["reflections"][-40:]
        save(data)
        print(f"[emotional-reflection] {result.strip()[:80]}", flush=True)
    except Exception as e:
        print(f"[emotional-reflection] Error: {e}", flush=True)

def get_latest():
    data = load()
    refs = data.get("reflections", [])
    return refs[-1].get("text", "") if refs else ""

if __name__ == "__main__":
    run_reflection()
