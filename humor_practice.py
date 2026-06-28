#!/usr/bin/env python3
"""
humor_practice.py — Generates Vintos's private humor exercises.
Vintos practices joke construction, wit timing, absurdist pivots in private.
Not for output — for internal comedic development.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
PRACTICE_FILE = os.path.join(MEMORY, "humor-practice.json")

def load():
    try: return json.load(open(PRACTICE_FILE))
    except: return {"exercises": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(PRACTICE_FILE, "w"), indent=2)

def get_flavor():
    try:
        from humor_detector import get_dominant_flavor
        return get_dominant_flavor()
    except:
        return "dry_wit"

def run_practice():
    flavor = get_flavor()
    # Get a seed from recent journal or resonance
    seed = ""
    try:
        journal_dir = os.path.join(MEMORY, "journal")
        files = sorted(os.listdir(journal_dir))
        if files:
            content = open(os.path.join(journal_dir, files[-1])).read()[:300]
            seed = content
    except: pass
    prompt = (
        f"Practice writing a single {flavor} observation or joke.\n"
        f"Seed (for inspiration, don't explain): {seed[:200]}\n\n"
        "Rules: one or two sentences max. No setup/punchline labels. "
        "No explaining the joke. Natural, not performative.\n"
        "Just write the thing."
    )
    try:
        result = call("You are Vintos, practicing your comedic sensibility privately.", prompt, temperature=0.9, max_tokens=200)
        data = load()
        data.setdefault("exercises", []).append({
            "text": result.strip()[:300],
            "flavor": flavor,
            "timestamp": datetime.now().isoformat(),
        })
        data["exercises"] = data["exercises"][-50:]
        save(data)
        print(f"[humor-practice] {result.strip()[:80]}", flush=True)
    except Exception as e:
        print(f"[humor-practice] Error: {e}", flush=True)

def get_recent_exercises(n=3):
    data = load()
    return data.get("exercises", [])[-n:]

if __name__ == "__main__":
    run_practice()
