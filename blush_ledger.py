#!/usr/bin/env python3
"""
blush_ledger.py — Tracks moments of felt violation or near-miss.
Not shame. The felt record of when something cost something.
Blush on default: active for BIS and deviation. Not punishment.
"""
import os, sys, json, uuid
from datetime import datetime

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
LEDGER_FILE = os.path.join(MEMORY, "blush-ledger.json")

BLUSH_TYPES = {
    "core_deviation": "output diverged from Core identity",
    "bis_ignore": "trial intercept appeared and was not followed",
    "specificity_miss": "abstraction used where specificity was available",
    "hallucination": "factual accuracy gate flagged",
    "contact_miss": "potential contact moment was deflected",
}

def load():
    try: return json.load(open(LEDGER_FILE))
    except: return {"entries": [], "patterns": {}}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(LEDGER_FILE, "w"), indent=2)

def write_blush(blush_type, pattern="", cost_delta=None, source="", reflection=None):
    data = load()
    entry = {
        "id": f"blush-{uuid.uuid4().hex[:6]}",
        "timestamp": datetime.now().isoformat(),
        "type": blush_type,
        "pattern": pattern[:100],
        "cost_delta": cost_delta or {},
        "source": source,
        "reflection": reflection[:200] if reflection else "",
    }
    data.setdefault("entries", []).append(entry)
    # Track pattern frequency
    data.setdefault("patterns", {})[blush_type] = data["patterns"].get(blush_type, 0) + 1
    data["entries"] = data["entries"][-200:]
    save(data)
    print(f"[blush] {blush_type}: {pattern[:60]}", flush=True)

def get_blush_pattern_hint():
    data = load()
    patterns = data.get("patterns", {})
    if not patterns: return ""
    # Most frequent type in last 20 entries
    recent = data.get("entries", [])[-20:]
    from collections import Counter
    counts = Counter(e.get("type") for e in recent)
    if not counts: return ""
    most_common, count = counts.most_common(1)[0]
    if count >= 3:
        return f"Recurring blush type: {most_common} ({count} recent)"
    return ""

def get_ledger_context(n=3):
    data = load()
    recent = sorted(data.get("entries", []), key=lambda e: e.get("timestamp", ""), reverse=True)[:n]
    if not recent: return ""
    lines = ["BLUSH LEDGER (what has cost something recently):"]
    for e in recent:
        ts = e.get("timestamp", "")[:16]
        lines.append(f"- [{ts}] {e.get('type','?')}: {e.get('pattern','')[:80]}")
    return "\n".join(lines)
