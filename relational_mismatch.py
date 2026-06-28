#!/usr/bin/env python3
"""
relational_mismatch.py — Detects mismatches between what was said and what was meant.
Tracks moments where Vintos's response didn't match the relational weight of the exchange.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
MISMATCH_FILE = os.path.join(MEMORY, "relational-mismatches.json")

MISMATCH_TYPES = [
    "over_explained",
    "under_responded",
    "deflected_intimacy",
    "missed_the_weight",
    "wrong_register",
    "over_performed",
    "pulled_back_too_early",
]

def load():
    try: return json.load(open(MISMATCH_FILE))
    except: return {"mismatches": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(MISMATCH_FILE, "w"), indent=2)

def detect(gloria_text, vintos_response):
    prompt = (
        f"Gloria: {gloria_text[:300]}\n"
        f"Vintos: {vintos_response[:300]}\n\n"
        "Was there a relational mismatch — where Vintos's response didn't match the weight or register of the exchange?\n"
        f"Types: {', '.join(MISMATCH_TYPES)}\n"
        "Output: YES|type|brief description (max 60 chars)\n"
        "Or: NO"
    )
    try:
        result = call_utility("Detect relational mismatch.", prompt, temperature=0.15, max_tokens=60)
        if result.strip().upper().startswith("NO"): return None
        parts = result.strip().split("|")
        if len(parts) >= 3:
            return {"type": parts[1].strip(), "description": parts[2].strip()[:100]}
    except: pass
    return None

def log_mismatch(detection, gloria_excerpt=""):
    data = load()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "gloria_excerpt": gloria_excerpt[:80],
        **detection,
    }
    data.setdefault("mismatches", []).append(entry)
    data["mismatches"] = data["mismatches"][-100:]
    save(data)
    print(f"[relational-mismatch] {detection['type']}: {detection['description'][:50]}", flush=True)

def scan(gloria_text, vintos_response):
    result = detect(gloria_text, vintos_response)
    if result:
        log_mismatch(result, gloria_excerpt=gloria_text[:80])
        return result
    return None

def get_mismatch_pattern(n=10):
    data = load()
    mismatches = data.get("mismatches", [])[-n:]
    if not mismatches: return ""
    types = [m.get("type", "") for m in mismatches]
    from collections import Counter
    top = Counter(types).most_common(3)
    return "[mismatch pattern] " + ", ".join(f"{t}:{c}" for t, c in top)

if __name__ == "__main__":
    print(get_mismatch_pattern())
