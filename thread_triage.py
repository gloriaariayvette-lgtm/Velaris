#!/usr/bin/env python3
"""
thread_triage.py — Classifies and prioritizes open conversational threads.
Threads: unresolved exchanges, lingering questions, ongoing tensions.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
THREADS_FILE = os.path.join(MEMORY, "thread-triage.json")

THREAD_TYPES = ["intellectual", "emotional", "relational", "creative", "existential", "practical"]
PRIORITY_LEVELS = ["dormant", "simmering", "active", "urgent"]

def load():
    try: return json.load(open(THREADS_FILE))
    except: return {"threads": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(THREADS_FILE, "w"), indent=2)

def add_thread(description, thread_type="", priority="simmering", source=""):
    data = load()
    # Check for duplicate
    for t in data.get("threads", []):
        if t.get("description", "")[:60] == description[:60] and not t.get("resolved"):
            t["priority"] = priority
            t["last_seen"] = datetime.now().isoformat()
            save(data)
            return t["id"]
    thread = {
        "id": f"thr-{uuid.uuid4().hex[:5]}",
        "description": description[:300],
        "type": thread_type or "intellectual",
        "priority": priority,
        "source": source,
        "created": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat(),
        "resolved": False,
        "resolution_notes": "",
    }
    data.setdefault("threads", []).append(thread)
    data["threads"] = data["threads"][-80:]
    save(data)
    return thread["id"]

def resolve_thread(thread_id, notes=""):
    data = load()
    for t in data.get("threads", []):
        if t.get("id") == thread_id:
            t["resolved"] = True
            t["resolved_at"] = datetime.now().isoformat()
            t["resolution_notes"] = notes[:200]
            break
    save(data)

def classify_and_add(text, source=""):
    """Auto-classify a piece of text as a thread."""
    prompt = (
        f"Text: {text[:400]}\n\n"
        "Is there an open thread here — something unresolved, a question hanging, a tension?\n"
        f"Thread types: {', '.join(THREAD_TYPES)}\n"
        f"Priority: {', '.join(PRIORITY_LEVELS)}\n"
        "Output: YES|type|priority|description (max 80 chars)\n"
        "Or: NO"
    )
    try:
        result = call_utility("Classify conversational thread.", prompt, temperature=0.1, max_tokens=60)
        if result.strip().upper().startswith("NO"): return None
        parts = result.strip().split("|")
        if len(parts) >= 4:
            t = parts[1].strip()
            p = parts[2].strip()
            desc = parts[3].strip()
            if desc:
                return add_thread(desc, thread_type=t, priority=p, source=source)
    except: pass
    return None

def get_active_threads(n=6):
    data = load()
    active = [t for t in data.get("threads", []) if not t.get("resolved")]
    active.sort(key=lambda t: PRIORITY_LEVELS.index(t.get("priority", "dormant")) if t.get("priority") in PRIORITY_LEVELS else 0, reverse=True)
    return active[:n]

def get_threads_context():
    threads = get_active_threads(5)
    if not threads: return ""
    lines = ["[open threads]"]
    for t in threads:
        p = t.get("priority", "?")
        desc = t.get("description", "")[:80]
        lines.append(f"  [{p}] {desc}")
    return "\n".join(lines)

if __name__ == "__main__":
    print(get_threads_context())
