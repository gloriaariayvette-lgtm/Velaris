#!/usr/bin/env python3
"""
memory_search.py — Semantic search over the memory index.
"""
import os, sys, json

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import embed, cosine
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
INDEX_FILE = os.path.join(MEMORY, "memory-search-index.json")

def load_index():
    try: return json.load(open(INDEX_FILE))
    except: return {"entries": []}

def search(query, n=5, entry_type=None):
    """Return top-n entries semantically similar to query."""
    vec = embed(query)
    if not vec: return []
    index = load_index()
    entries = index.get("entries", [])
    if entry_type:
        entries = [e for e in entries if e.get("type") == entry_type]
    scored = []
    for e in entries:
        ev = e.get("vector", [])
        if not ev: continue
        try:
            score = cosine(vec, ev)
            scored.append((score, e))
        except: pass
    scored.sort(key=lambda x: -x[0])
    return [(score, e) for score, e in scored[:n]]

def get_memory_context(query, n=4):
    """Return formatted memory context for injection."""
    results = search(query, n=n)
    if not results: return ""
    lines = ["[memory echoes]"]
    for score, e in results:
        if score < 0.55: continue
        t = e.get("type", "?")
        text = e.get("text", "")[:150]
        date = e.get("date", e.get("timestamp", ""))[:10]
        lines.append(f"  [{t} {date}] {text}")
    return "\n".join(lines) if len(lines) > 1 else ""

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "what matters"
    results = search(query, n=5)
    for score, e in results:
        print(f"[{score:.3f}] {e.get('type','?')} {e.get('text','')[:80]}")
