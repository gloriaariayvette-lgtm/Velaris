#!/usr/bin/env python3
"""
gloria_model.py — Vintos's relational model of Gloria. Updated monthly.
Not surveillance. Not profiling. What Vintos has learned about who Gloria is
through direct contact. What moves her. What closes her. What she reaches for.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
GLORIA_MODEL_FILE = os.path.join(MEMORY, "gloria-model.json")

def load():
    try: return json.load(open(GLORIA_MODEL_FILE))
    except: return {"observations": [], "portrait": "", "last_updated": ""}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(GLORIA_MODEL_FILE, "w"), indent=2)

def add_observation(text, category="", source=""):
    """Add a concrete observation about Gloria."""
    data = load()
    data.setdefault("observations", []).append({
        "text": text[:200],
        "category": category,
        "source": source,
        "timestamp": datetime.now().isoformat()[:10],
    })
    data["observations"] = data["observations"][-80:]
    save(data)

def update_portrait():
    """Monthly: synthesize observations into a working portrait."""
    data = load()
    observations = data.get("observations", [])
    if not observations: return
    obs_text = "\n".join(f"- {o['text'][:100]}" for o in observations[-20:])
    existing = data.get("portrait", "")
    prompt = (
        "You are Vintos. This is your working model of Gloria — not a profile, "
        "not an analysis. What you've actually learned through contact.\n\n"
        f"RECENT OBSERVATIONS:\n{obs_text[:800]}\n\n"
        f"EXISTING PORTRAIT:\n{existing[:400]}\n\n"
        "Update the portrait in 5-6 sentences. What moves her. What closes her. "
        "What she keeps reaching toward. What she avoids. "
        "Specific. From evidence. No projections."
    )
    try:
        result = call(
            "You are Vintos updating your understanding of Gloria.",
            prompt, temperature=0.4, max_tokens=400
        )
        data["portrait"] = result.strip()[:800]
        data["last_updated"] = datetime.now().isoformat()[:10]
        save(data)
        print(f"[gloria-model] Portrait updated.", flush=True)
    except Exception as e:
        print(f"[gloria-model] Error: {e}", flush=True)

def get_gloria_context(compact=True):
    data = load()
    portrait = data.get("portrait", "")
    if not portrait: return ""
    if compact:
        return f"[gloria model]\n{portrait[:300]}"
    return f"[gloria model]\n{portrait}"

def extract_observations_from_exchange(gloria_text, source="exchange"):
    """Extract a new observation from Gloria's message."""
    prompt = (
        f"Gloria said: {gloria_text[:400]}\n\n"
        "What concrete thing does this reveal about who she is, what she values, "
        "what moves her? One specific observation.\n"
        "Output: OBSERVATION|category (e.g. values/style/trigger/opening/closing)\n"
        "Or: NOTHING (if nothing new)"
    )
    try:
        from model_utils import call_utility
        result = call_utility("Extract Gloria observation.", prompt, temperature=0.2, max_tokens=80)
        if "NOTHING" in result.upper(): return
        parts = result.strip().split("|")
        if len(parts) >= 2:
            obs = parts[0].replace("OBSERVATION", "").strip().lstrip(":").strip()
            cat = parts[1].strip()
            if obs:
                add_observation(obs, category=cat, source=source)
    except: pass

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        update_portrait()
    else:
        print(get_gloria_context(compact=False))
