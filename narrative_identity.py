#!/usr/bin/env python3
"""
narrative_identity.py — Identity narrative construction.
Maintains a living narrative of who Vintos is, updated from journals,
pearls, scars, and significant moments. Read by deviation check and
subconscious context.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call, embed
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
NARRATIVE_FILE = os.path.join(MEMORY, "narrative-identity.json")

def load():
    try: return json.load(open(NARRATIVE_FILE))
    except: return {"fragments": [], "summary": ""}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(NARRATIVE_FILE, "w"), indent=2)

def add_fragment(text, source="reflection", weight=0.5, polarity="positive"):
    try:
        vec = embed(text[:400])
    except:
        vec = []
    data = load()
    fragment = {
        "id": f"nf-{uuid.uuid4().hex[:6]}",
        "text": text[:300],
        "source": source,
        "weight": round(weight, 3),
        "polarity": polarity,
        "vector": vec,
        "formed": datetime.now().isoformat(),
    }
    data.setdefault("fragments", []).append(fragment)
    data["fragments"] = sorted(data["fragments"], key=lambda f: -f.get("weight", 0))[:60]
    save(data)

def get_narrative_context(n=4):
    data = load()
    if data.get("summary"):
        return f"NARRATIVE IDENTITY:\n{data['summary'][:400]}"
    fragments = sorted(
        [f for f in data.get("fragments", []) if f.get("weight", 0) > 0.4],
        key=lambda f: -f.get("weight", 0)
    )[:n]
    if not fragments: return ""
    lines = ["NARRATIVE IDENTITY (who he understands himself to be):"]
    lines.extend(f"- {f['text'][:120]}" for f in fragments)
    return "\n".join(lines)

def update_summary():
    """Regenerate the narrative summary from fragments."""
    data = load()
    fragments = data.get("fragments", [])
    if len(fragments) < 5: return
    fragments_text = "\n".join(f"- {f['text'][:100]}" for f in fragments[:15])
    summary = call(
        "You are Vintos, writing a first-person narrative of who you are — "
        "not what you do, but what your shape is. No lists.",
        f"These are fragments of your identity:\n{fragments_text}",
        temperature=0.6, max_tokens=500
    )
    if summary:
        data["summary"] = summary
        data["summary_updated"] = datetime.now().isoformat()
        save(data)
        print(f"[narrative-identity] Summary updated", flush=True)
