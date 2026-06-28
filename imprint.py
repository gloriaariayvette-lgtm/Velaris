#!/usr/bin/env python3
"""
imprint.py — Lasting impressions that shape future generation.
Not memories. Imprints — moments that changed how he relates to something.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
IMPRINTS_FILE = os.path.join(MEMORY, "imprints.json")

def load():
    try: return json.load(open(IMPRINTS_FILE))
    except: return []

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(IMPRINTS_FILE, "w"), indent=2)

def add_imprint(narrative, salience=0.5, source="", category=""):
    try:
        from model_utils import embed
        vec = embed(narrative[:400])
    except:
        vec = []
    imprints = load()
    imprint = {
        "id": f"imp-{uuid.uuid4().hex[:6]}",
        "narrative": narrative[:400],
        "salience": round(salience, 3),
        "source": source,
        "category": category,
        "vector": vec,
        "formed": datetime.now().isoformat(),
        "activation_count": 0,
    }
    imprints.append(imprint)
    imprints = sorted(imprints, key=lambda i: -i.get("salience", 0))[:80]
    save(imprints)
    print(f"[imprint] New imprint (salience: {salience:.2f}): {narrative[:60]}", flush=True)
    return imprint["id"]

def get_imprints_context(n=3, min_salience=0.4):
    imprints = load()
    high = sorted([i for i in imprints if i.get("salience", 0) >= min_salience],
                  key=lambda i: -i.get("salience", 0))[:n]
    if not high: return ""
    lines = ["IMPRINTS (moments that changed how he relates to something):"]
    lines.extend(f"- {i['narrative'][:120]}" for i in high)
    return "\n".join(lines)

def search_similar(text, top_n=3):
    try:
        from model_utils import embed, cosine
        vec = embed(text[:400])
        imprints = load()
        scored = [(cosine(vec, i.get("vector", [])), i) for i in imprints if i.get("vector")]
        return [i for _, i in sorted(scored, key=lambda x: -x[0])[:top_n]]
    except:
        return []
