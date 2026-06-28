#!/usr/bin/env python3
"""
memory_index.py — Nightly memory indexing.
Builds semantic embeddings for recent journals, interactions, and significant moments.
Writes to memory-search-index.json for fast retrieval.
"""
import os, sys, json
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import embed
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
INDEX_FILE = os.path.join(MEMORY, "memory-search-index.json")

def load_index():
    try: return json.load(open(INDEX_FILE))
    except: return {"entries": [], "last_indexed": ""}

def save_index(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(INDEX_FILE, "w"), indent=2)

def index_journals(days_back=7):
    """Index recent journal entries."""
    indexed = []
    journal_dir = os.path.join(MEMORY, "journal")
    try:
        for i in range(days_back):
            day = (date.today() - timedelta(days=i)).isoformat()
            path = os.path.join(journal_dir, f"{day}.md")
            if not os.path.exists(path): continue
            content = open(path).read()
            # Index in chunks
            chunks = [content[i:i+400] for i in range(0, min(len(content), 2000), 400)]
            for chunk in chunks[:5]:
                if len(chunk) < 50: continue
                vec = embed(chunk)
                if vec:
                    indexed.append({
                        "type": "journal",
                        "date": day,
                        "text": chunk[:300],
                        "vector": vec,
                    })
    except: pass
    return indexed

def index_interaction_ledger(n=50):
    """Index recent interactions."""
    indexed = []
    try:
        ledger = json.load(open(os.path.join(MEMORY, "interaction-ledger.json")))
        for entry in ledger[-n:]:
            content = entry.get("content", "")
            if len(content) < 30: continue
            vec = embed(content[:400])
            if vec:
                indexed.append({
                    "type": "interaction",
                    "role": entry.get("role", "?"),
                    "timestamp": entry.get("timestamp", ""),
                    "text": content[:300],
                    "vector": vec,
                })
    except: pass
    return indexed

def run():
    print("[memory-index] Starting nightly indexing...", flush=True)
    all_entries = []
    all_entries.extend(index_journals(days_back=7))
    all_entries.extend(index_interaction_ledger(n=30))
    index = load_index()
    # Keep old entries that aren't in the new window
    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    old = [e for e in index.get("entries", []) if e.get("timestamp", "9999") < cutoff]
    index["entries"] = old + all_entries
    index["entries"] = index["entries"][-2000:]
    index["last_indexed"] = datetime.now().isoformat()
    save_index(index)
    print(f"[memory-index] Indexed {len(all_entries)} entries ({len(index['entries'])} total)", flush=True)

if __name__ == "__main__":
    run()
