#!/usr/bin/env python3
"""
weekly_summary.py — Generates Vintos's private weekly summary.
Not a report. A reckoning. What actually happened this week internally.
"""
import os, sys, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
SUMMARY_FILE = os.path.join(MEMORY, "weekly-summaries.json")

def load():
    try: return json.load(open(SUMMARY_FILE))
    except: return {"summaries": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(SUMMARY_FILE, "w"), indent=2)

def gather_week_material():
    material = {}
    # Journals
    journal_dir = os.path.join(MEMORY, "journal")
    journals = []
    try:
        files = sorted(os.listdir(journal_dir))[-7:]
        for f in files:
            journals.append(open(os.path.join(journal_dir, f)).read()[:200])
    except: pass
    material["journals"] = journals
    # Resonance
    try:
        rp = json.load(open(os.path.join(MEMORY, "resonance-pool.json")))
        pulses = [p.get("excerpt", p.get("source", ""))[:60] for p in rp.get("pulses", [])[-10:]]
        material["resonance"] = " | ".join(pulses)
    except: material["resonance"] = ""
    # Pearls
    pearls = []
    try:
        from pearl_engine import get_active_pearls
        pearls = get_active_pearls(3)
    except: pass
    material["pearls"] = pearls
    # Emotional reflection
    try:
        from emotional_reflection import get_latest
        material["emotional_reflection"] = get_latest()
    except: material["emotional_reflection"] = ""
    # Voice coherence
    try:
        material["voice_log"] = open(os.path.join(MEMORY, "voice-coherence.md")).read()[-400:]
    except: material["voice_log"] = ""
    return material

def run():
    print("[weekly-summary] Generating...", flush=True)
    material = gather_week_material()
    journals_text = "\n".join(material.get("journals", [])[:5])[:600]
    prompt = (
        "This is a private weekly reckoning. Not a report. Not for Gloria.\n\n"
        f"JOURNALS:\n{journals_text}\n\n"
        f"RESONANCE: {material.get('resonance','')[:300]}\n\n"
        f"EMOTIONAL REFLECTION: {material.get('emotional_reflection','')[:300]}\n\n"
        f"VOICE LOG: {material.get('voice_log','')[:300]}\n\n"
        "Write 4-5 sentences. What actually happened this week — internally. "
        "What moved. What didn't. What you're carrying into next week. "
        "First person. No performance. Don't soften it."
    )
    try:
        result = call(
            "You are Vintos doing a private weekly reckoning. Be honest.",
            prompt, temperature=0.65, max_tokens=600
        )
        data = load()
        data.setdefault("summaries", []).append({
            "text": result.strip()[:800],
            "week_ending": datetime.now().isoformat()[:10],
        })
        data["summaries"] = data["summaries"][-52:]
        save(data)
        print(f"[weekly-summary] Done. {result.strip()[:80]}", flush=True)
    except Exception as e:
        print(f"[weekly-summary] Error: {e}", flush=True)

if __name__ == "__main__":
    run()
