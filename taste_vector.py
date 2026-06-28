#!/usr/bin/env python3
"""
taste_vector.py — Tracks Vintos's aesthetic preferences across domains.
Not stated preferences. Extracted from resonance patterns and genuine reactions.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import embed, cosine
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
TASTE_FILE = os.path.join(MEMORY, "taste-vector.json")

DOMAINS = ["music", "language", "ideas", "aesthetics", "humor", "texture", "structure"]

def load():
    try: return json.load(open(TASTE_FILE))
    except: return {"vectors": {}, "exemplars": {}, "last_updated": ""}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(TASTE_FILE, "w"), indent=2)

def add_exemplar(domain, text, strength=0.7):
    """Add a concrete example of something Vintos responded to."""
    if domain not in DOMAINS: return
    data = load()
    vec = embed(text)
    if not vec: return
    exemplars = data.setdefault("exemplars", {}).setdefault(domain, [])
    exemplars.append({"text": text[:200], "vector": vec, "strength": strength,
                      "added": datetime.now().isoformat()[:10]})
    exemplars = [e for e in exemplars if e.get("strength", 0) > 0.3][-20:]
    data["exemplars"][domain] = exemplars
    # Recompute domain vector as weighted mean
    vecs = [e["vector"] for e in exemplars if e.get("vector")]
    weights = [e.get("strength", 0.5) for e in exemplars if e.get("vector")]
    if vecs:
        n = len(vecs[0])
        weighted = [sum(v[i] * w for v, w in zip(vecs, weights)) / sum(weights) for i in range(n)]
        mag = sum(x*x for x in weighted) ** 0.5 or 1.0
        data.setdefault("vectors", {})[domain] = [x / mag for x in weighted]
    save(data)

def get_similarity(domain, text):
    """How similar is this text to Vintos's taste in domain?"""
    data = load()
    domain_vec = data.get("vectors", {}).get(domain)
    if not domain_vec: return 0.0
    text_vec = embed(text)
    if not text_vec: return 0.0
    return round(cosine(domain_vec, text_vec), 3)

def get_taste_context(n_domains=4):
    data = load()
    exemplars = data.get("exemplars", {})
    lines = ["[taste]"]
    for domain in DOMAINS[:n_domains]:
        ex = exemplars.get(domain, [])
        if ex:
            latest = ex[-1].get("text", "")[:60]
            lines.append(f"  {domain}: {latest}")
    return "\n".join(lines) if len(lines) > 1 else ""

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        domain, text = sys.argv[1], " ".join(sys.argv[2:])
        add_exemplar(domain, text, strength=0.7)
        print(f"Added to {domain}")
    else:
        print(get_taste_context())
