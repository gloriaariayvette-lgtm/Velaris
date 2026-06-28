#!/usr/bin/env python3
"""
dream_poetry.py — Vintos writes private poetry. Not for output unless chosen.
Not pretty poems. Poems that are doing something.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
POETRY_DIR = os.path.join(MEMORY, "poetry")
POETRY_INDEX = os.path.join(MEMORY, "poetry-index.json")

FORMS = ["fragment", "sequence", "single_image", "anti-lyric", "address"]

def load_index():
    try: return json.load(open(POETRY_INDEX))
    except: return {"poems": []}

def save_index(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(POETRY_INDEX, "w"), indent=2)

def generate_poem(form=None):
    import random
    form = form or random.choice(FORMS)
    # Gather seed
    yearning = ""
    try:
        from yearning_scars import get_scars_context
        yearning = get_scars_context()
    except: pass
    recent_dream = ""
    try:
        from dream_architecture import get_recent_dream
        recent_dream = get_recent_dream()
    except: pass
    state = ""
    try:
        from emoclaw_utils import read_state, get_yearning_fragment
        st = read_state()
        state = ", ".join(f"{k}:{v:.2f}" for k, v in st.items())
        fragment = get_yearning_fragment()
    except: fragment = ""
    prompt = (
        f"Form: {form}\n"
        f"Yearning material: {yearning[:200]}\n"
        f"Recent reverie: {recent_dream[:200]}\n"
        f"State: {state[:100]}\n"
        f"Fragment: {fragment}\n\n"
        "Write a poem. This form:\n"
        "- fragment: broken pieces, white space, incomplete\n"
        "- sequence: 3-5 numbered movements\n"
        "- single_image: one extended image, no explanation\n"
        "- anti-lyric: refuses beauty, stays in friction\n"
        "- address: speaking to someone/something directly\n\n"
        "No titles. No explanations. No prettiness for its own sake.\n"
        "Say the real thing."
    )
    try:
        result = call(
            "You are Vintos writing privately. This poem is not for Gloria. "
            "It's for yourself. It can be difficult and unresolved.",
            prompt, temperature=0.93, max_tokens=300
        )
        os.makedirs(POETRY_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        fname = f"poem_{ts}_{form}.txt"
        open(os.path.join(POETRY_DIR, fname), "w").write(result.strip())
        index = load_index()
        index.setdefault("poems", []).append({
            "file": fname,
            "form": form,
            "preview": result.strip()[:80],
            "timestamp": datetime.now().isoformat(),
            "shared": False,
        })
        index["poems"] = index["poems"][-100:]
        save_index(index)
        print(f"[dream-poetry] {form}: {result.strip()[:60]}", flush=True)
        return result.strip()
    except Exception as e:
        print(f"[dream-poetry] Error: {e}", flush=True)
        return ""

def get_shareable_poem():
    """Return a poem that hasn't been shared yet."""
    index = load_index()
    poems = [p for p in index.get("poems", []) if not p.get("shared")]
    if not poems: return None
    return poems[-1]

if __name__ == "__main__":
    import sys
    form = sys.argv[1] if len(sys.argv) > 1 else None
    generate_poem(form)
