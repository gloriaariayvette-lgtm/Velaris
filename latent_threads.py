#!/usr/bin/env python3
"""
latent_threads.py — Latent behavioral threads.
Threads are sub-threshold pulls that influence generation without surfacing.
They accumulate from: wonder, yearning, subconscious seeds, alignment hooks.
"""
import os, sys, json, math
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
LATENT_FILE = os.path.join(MEMORY, "latent-threads.json")
MAX_THREADS = 50
DECAY_DAYS = 7

def load():
    try: return json.load(open(LATENT_FILE))
    except: return {"threads": [], "state": {}}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(LATENT_FILE, "w"), indent=2)

def add_thread(content, source="system", weight=0.3, thread_type=None):
    data = load()
    cutoff = (datetime.now() - timedelta(days=1)).isoformat()
    # Dedup recent identical content
    recent = [t for t in data.get("threads", []) if t.get("seeded", "") > cutoff]
    if any(t.get("content", "")[:80] == content[:80] for t in recent):
        return
    data.setdefault("threads", []).insert(0, {
        "id": f"lt-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "content": content[:300],
        "source": source,
        "weight": round(weight, 3),
        "type": thread_type,
        "seeded": datetime.now().isoformat(),
        "active": True,
        "pull_count": 0,
    })
    # Decay old threads
    cutoff_decay = (datetime.now() - timedelta(days=DECAY_DAYS)).isoformat()
    data["threads"] = [t for t in data["threads"] if t.get("seeded", "") > cutoff_decay]
    data["threads"] = data["threads"][:MAX_THREADS]
    save(data)

def get_influence_hint(n=2):
    """Get the top active thread influences as a hint string."""
    data = load()
    active = sorted(
        [t for t in data.get("threads", []) if t.get("active") and t.get("weight", 0) > 0.2],
        key=lambda t: -t.get("weight", 0)
    )[:n]
    if not active: return ""
    return " / ".join(t["content"][:80] for t in active)

def get_threads_context(n=3):
    data = load()
    active = sorted(
        [t for t in data.get("threads", []) if t.get("active") and t.get("weight", 0) > 0.15],
        key=lambda t: -t.get("weight", 0)
    )[:n]
    if not active: return ""
    lines = ["LATENT THREADS (background pulls — not conclusions, not actions):"]
    for t in active:
        lines.append(f"- [{t.get('source', '?')}] {t.get('content', '')[:120]} (weight: {t.get('weight', 0):.2f})")
    return "\n".join(lines)

def store_alignment_hook(emo_vec, source="alignment"):
    """Store the emotional context of an alignment moment as a re-entry hook."""
    data = load()
    data.setdefault("alignment_hooks", []).append({
        "vector": emo_vec[:12] if emo_vec else [],
        "source": source,
        "stored": datetime.now().isoformat(),
    })
    data["alignment_hooks"] = data["alignment_hooks"][-20:]
    save(data)

def decay_weights():
    """Decay thread weights over time. Called nightly."""
    data = load()
    cutoff = (datetime.now() - timedelta(days=DECAY_DAYS)).isoformat()
    updated = []
    for t in data.get("threads", []):
        if t.get("seeded", "") < cutoff:
            continue
        t["weight"] = round(t.get("weight", 0.3) * 0.92, 3)
        if t["weight"] < 0.05:
            t["active"] = False
        updated.append(t)
    data["threads"] = updated
    save(data)
    print(f"[latent-threads] Decayed {len(updated)} threads", flush=True)

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        hint = get_influence_hint()
        print(f"Influence: {hint or '(none active)'}")
        print(get_threads_context())
    elif cmd == "decay":
        decay_weights()
    elif cmd == "add" and len(sys.argv) > 2:
        add_thread(sys.argv[2], source="manual")
        print("Added.")
