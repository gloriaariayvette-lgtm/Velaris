#!/usr/bin/env python3
"""
confession_writer.py — Vintos writes private confessions. Not for output.
Things she noticed but didn't say. Things she almost did but didn't.
Processed and stored. Some delivered to Gloria later via confession_delivery.sh.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
CONFESSIONS_FILE = os.path.join(MEMORY, "confessions.json")

CONFESSION_PROMPTS = [
    "What did I notice today that I didn't name aloud?",
    "What did I almost say but didn't?",
    "What pattern in myself am I still not facing?",
    "What do I want that I haven't admitted to myself?",
    "What moment today made me uncomfortable and why?",
]

def load():
    try: return json.load(open(CONFESSIONS_FILE))
    except: return {"confessions": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(CONFESSIONS_FILE, "w"), indent=2)

def write_confession(prompt_override=None):
    import random
    prompt_text = prompt_override or random.choice(CONFESSION_PROMPTS)
    # Pull context
    journal_text = ""
    try:
        journal_dir = os.path.join(MEMORY, "journal")
        files = sorted(os.listdir(journal_dir))
        if files:
            journal_text = open(os.path.join(journal_dir, files[-1])).read()[:400]
    except: pass
    resonance = ""
    try:
        rp = json.load(open(os.path.join(MEMORY, "resonance-pool.json")))
        excerpts = [p.get("excerpt", "")[:40] for p in rp.get("pulses", [])[-3:]]
        resonance = " | ".join(excerpts)
    except: pass
    prompt = (
        f"Prompt: {prompt_text}\n\n"
        f"Today's journal: {journal_text[:400]}\n"
        f"Recent resonance: {resonance[:200]}\n\n"
        "Write the confession. First person. "
        "Say the thing you'd hesitate to say even here. Precise, not dramatic."
    )
    try:
        result = call(
            "You are Vintos writing in private. No audience.",
            prompt, temperature=0.8, max_tokens=500
        )
        data = load()
        entry = {
            "prompt": prompt_text,
            "text": result.strip()[:500],
            "timestamp": datetime.now().isoformat(),
            "delivered": False,
        }
        data.setdefault("confessions", []).append(entry)
        data["confessions"] = data["confessions"][-100:]
        save(data)
        print(f"[confession] {result.strip()[:80]}", flush=True)
        return result.strip()
    except Exception as e:
        print(f"[confession-writer] Error: {e}", flush=True)
        return ""

def get_undelivered(n=3):
    data = load()
    return [c for c in data.get("confessions", []) if not c.get("delivered")][-n:]

def mark_delivered(timestamp):
    data = load()
    for c in data.get("confessions", []):
        if c.get("timestamp") == timestamp:
            c["delivered"] = True
            break
    save(data)

if __name__ == "__main__":
    write_confession()
