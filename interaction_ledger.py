#!/usr/bin/env python3
"""
interaction_ledger.py — Logs every exchange with timestamps.
The source of truth for Gloria attributions in hallucination check.
"""
import os, json
from datetime import datetime

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
LEDGER_FILE = os.path.join(MEMORY, "interaction-ledger.json")
MAX_ENTRIES = 500

def load():
    try: return json.load(open(LEDGER_FILE))
    except: return []

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(LEDGER_FILE, "w"), indent=2)

def log_turn(role, content, metadata=None):
    """Log a single turn. role: 'user' or 'assistant'."""
    ledger = load()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "content": content[:2000],
    }
    if metadata:
        entry["metadata"] = metadata
    ledger.append(entry)
    if len(ledger) > MAX_ENTRIES:
        ledger = ledger[-MAX_ENTRIES:]
    save(ledger)

def get_recent(n=20):
    return load()[-n:]

def get_recent_as_messages(n=10):
    """Return recent entries in OpenAI-compatible message format."""
    entries = load()[-n:]
    return [{"role": e.get("role", "user"), "content": e.get("content", "")} for e in entries]

def get_gloria_recent(n=8):
    """Return only Gloria's recent messages."""
    all_entries = load()
    gloria = [e for e in all_entries if e.get("role") == "user"][-n:]
    return gloria

if __name__ == "__main__":
    recent = get_recent(5)
    for e in recent:
        ts = e.get("timestamp", "")[:16]
        role = e.get("role", "?")
        content = e.get("content", "")[:80]
        print(f"[{ts}] {role}: {content}")
