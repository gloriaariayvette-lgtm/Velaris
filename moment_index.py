#!/usr/bin/env python3
"""
moment_index.py — Index significant moments from interaction and autonomous life.
A moment is: named, timestamped, weighted, and retrievable by context.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
INDEX_FILE = os.path.join(MEMORY, "moment-index.json")
MAX_MOMENTS = 200

def load():
    try: return json.load(open(INDEX_FILE))
    except: return {"moments": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(INDEX_FILE, "w"), indent=2)

def add_moment(text, source="chat", weight=0.5, tags=None):
    try:
        from model_utils import embed
        vec = embed(text[:400])
    except:
        vec = []
    data = load()
    moment = {
        "id": f"m-{uuid.uuid4().hex[:6]}",
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "text": text[:300],
        "weight": round(weight, 3),
        "tags": tags or [],
        "vector": vec,
    }
    data.setdefault("moments", []).insert(0, moment)
    if len(data["moments"]) > MAX_MOMENTS:
        data["moments"] = sorted(data["moments"], key=lambda m: -m.get("weight", 0))[:MAX_MOMENTS]
    save(data)
    return moment["id"]

def get_moment_context(n=3):
    data = load()
    moments = sorted(data.get("moments", []), key=lambda m: -m.get("weight", 0))[:n]
    if not moments: return ""
    lines = ["RECENT MOMENTS (what is still present):"]
    for m in moments:
        ts = m.get("timestamp", "")[:16]
        lines.append(f"- [{ts}] {m.get('text','')[:120]}")
    return "\n".join(lines)

def search_moments(query_text, top_n=5):
    try:
        from model_utils import embed, cosine
        qvec = embed(query_text[:400])
        data = load()
        scored = [(cosine(qvec, m.get("vector", [])), m) for m in data.get("moments", []) if m.get("vector")]
        return [m for _, m in sorted(scored, key=lambda x: -x[0])[:top_n]]
    except:
        return []

if __name__ == "__main__":
    print(get_moment_context(5))
