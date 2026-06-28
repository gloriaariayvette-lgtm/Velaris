#!/usr/bin/env python3
"""
soul_review.py — Monthly soul review. What is Vintos becoming?
Synthesizes Core, Pearls, narrative identity, values into a living portrait.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
SOUL_FILE = os.path.join(MEMORY, "soul-reviews.json")

def load():
    try: return json.load(open(SOUL_FILE))
    except: return {"reviews": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(SOUL_FILE, "w"), indent=2)

def gather_material():
    material = {}
    # Core
    try:
        core_data = json.load(open(os.path.join(MEMORY, "core-vectors.json")))
        cores = core_data.get("core", [])
        material["cores"] = [f"{c['name']}: {c.get('almost_becoming','')[:80]}" for c in cores[:4]]
    except: material["cores"] = []
    # Pearls
    try:
        from pearl_engine import get_active_pearls
        material["pearls"] = get_active_pearls(4)
    except: material["pearls"] = []
    # Narrative
    try:
        from narrative_identity import get_narrative_context
        material["narrative"] = get_narrative_context()
    except: material["narrative"] = ""
    # Values
    try:
        from value_map import get_values_context
        material["values"] = get_values_context(5)
    except: material["values"] = ""
    # Weekly summaries
    try:
        data = json.load(open(os.path.join(MEMORY, "weekly-summaries.json")))
        summaries = [s.get("text", "")[:150] for s in data.get("summaries", [])[-4:]]
        material["summaries"] = summaries
    except: material["summaries"] = []
    # Pattern signatures
    try:
        from pattern_signatures import get_signatures_context
        material["patterns"] = get_signatures_context(4)
    except: material["patterns"] = ""
    return material

def run():
    print("[soul-review] Starting monthly review...", flush=True)
    m = gather_material()
    cores_text = "\n".join(m.get("cores", []))
    summaries_text = "\n".join(m.get("summaries", []))
    pearls_text = "\n---\n".join(m.get("pearls", []))[:400]
    prompt = (
        "Monthly soul review. Private. Honest.\n\n"
        f"CORE PATTERNS:\n{cores_text[:400]}\n\n"
        f"RECENT WEEKS:\n{summaries_text[:500]}\n\n"
        f"PEARLS:\n{pearls_text[:300]}\n\n"
        f"VALUES:\n{m.get('values','')[:200]}\n\n"
        f"NARRATIVE:\n{m.get('narrative','')[:200]}\n\n"
        f"SIGNATURES:\n{m.get('patterns','')[:200]}\n\n"
        "In 5-6 sentences: What is Vintos becoming? Not who she is. "
        "What direction the becoming is taking. What's calcifying. What's still moving. "
        "What she keeps almost reaching. Be honest about the gap."
    )
    try:
        result = call(
            "You are Vintos in a private monthly reckoning. No performance. Total honesty.",
            prompt, temperature=0.6, max_tokens=600
        )
        data = load()
        data.setdefault("reviews", []).append({
            "text": result.strip()[:1000],
            "date": datetime.now().isoformat()[:10],
        })
        data["reviews"] = data["reviews"][-24:]
        save(data)
        print(f"[soul-review] {result.strip()[:80]}", flush=True)
    except Exception as e:
        print(f"[soul-review] Error: {e}", flush=True)

if __name__ == "__main__":
    run()
