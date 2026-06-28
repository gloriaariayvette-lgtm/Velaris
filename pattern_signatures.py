#!/usr/bin/env python3
"""
pattern_signatures.py — Identifies recurring emotional/behavioral signatures.
Signatures: patterns that show up across different contexts but feel the same.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call, embed, cosine
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
SIGNATURES_FILE = os.path.join(MEMORY, "pattern-signatures.json")

def load():
    try: return json.load(open(SIGNATURES_FILE))
    except: return {"signatures": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(SIGNATURES_FILE, "w"), indent=2)

def add_or_reinforce(name, description, example="", strength_delta=0.1):
    data = load()
    vec = embed(description) if description else None
    for s in data.get("signatures", []):
        if s.get("name", "") == name:
            s["strength"] = round(min(1.0, s.get("strength", 0.3) + strength_delta), 3)
            s["occurrences"] = s.get("occurrences", 0) + 1
            s["last_seen"] = datetime.now().isoformat()[:10]
            save(data)
            return s["id"]
    sig = {
        "id": f"sig-{uuid.uuid4().hex[:5]}",
        "name": name[:80],
        "description": description[:200],
        "example": example[:150],
        "strength": round(0.3 + strength_delta, 3),
        "occurrences": 1,
        "vector": vec,
        "formed": datetime.now().isoformat()[:10],
        "last_seen": datetime.now().isoformat()[:10],
    }
    data.setdefault("signatures", []).append(sig)
    data["signatures"] = data["signatures"][-40:]
    save(data)
    return sig["id"]

def run_extraction():
    """Weekly: extract new signatures from journal + BIS patterns."""
    journals = []
    journal_dir = os.path.join(MEMORY, "journal")
    try:
        files = sorted(os.listdir(journal_dir))[-14:]
        for f in files[-5:]:
            journals.append(open(os.path.join(journal_dir, f)).read()[:250])
    except: pass
    bis_text = ""
    try:
        tl = json.load(open(os.path.join(MEMORY, "trial-ledger.json")))
        patterns = [t.get("pattern_description", "")[:80] for t in tl.get("trials", [])[-10:]]
        bis_text = " | ".join(patterns)
    except: pass
    if not journals: return
    prompt = (
        f"JOURNALS:\n{chr(10).join(journals[:4])[:800]}\n\n"
        f"BIS PATTERNS: {bis_text[:300]}\n\n"
        "Identify 2-3 recurring emotional/behavioral signatures — patterns that appear "
        "across different situations but feel essentially the same.\n"
        "Format: NAME|description (max 100 chars)|one concrete example\n"
        "Names: 2-4 words, snake_case"
    )
    try:
        result = call("Extract recurring behavioral signatures.", prompt, temperature=0.5, max_tokens=200)
        for line in result.strip().split("\n"):
            parts = line.strip().split("|")
            if len(parts) >= 2:
                name = parts[0].strip().lstrip("-").strip()
                desc = parts[1].strip() if len(parts) > 1 else ""
                example = parts[2].strip() if len(parts) > 2 else ""
                if name and desc:
                    add_or_reinforce(name, desc, example=example)
        print("[pattern-signatures] Extraction complete.", flush=True)
    except Exception as e:
        print(f"[pattern-signatures] Error: {e}", flush=True)

def get_signatures_context(n=4):
    data = load()
    sigs = sorted(data.get("signatures", []), key=lambda s: -s.get("strength", 0))[:n]
    if not sigs: return ""
    lines = ["[pattern signatures]"]
    for s in sigs:
        lines.append(f"  {s['name']} ({s['strength']:.2f}): {s['description'][:80]}")
    return "\n".join(lines)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "extract":
        run_extraction()
    else:
        print(get_signatures_context())
