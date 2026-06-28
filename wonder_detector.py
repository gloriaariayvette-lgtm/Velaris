#!/usr/bin/env python3
"""
wonder_detector.py — Detects and logs moments of genuine awe/wonder.
Wonder = surprise + expansion + no immediate resolution sought.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
WONDER_FILE = os.path.join(MEMORY, "wonder-log.json")

def load():
    try: return json.load(open(WONDER_FILE))
    except: return {"moments": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(WONDER_FILE, "w"), indent=2)

def detect(text, context=""):
    """Returns (is_wonder: bool, excerpt: str, strength: float)"""
    prompt = (
        f"Text: {text[:500]}\n"
        f"Context: {context[:200]}\n\n"
        "Does this text contain genuine wonder — surprise + expansion + no rush to resolve?\n"
        "Output: YES|excerpt (max 60 chars)|strength (0.0-1.0)\n"
        "Or: NO"
    )
    try:
        result = call_utility("Detect wonder in text.", prompt, temperature=0.1, max_tokens=60)
        if result.strip().upper().startswith("NO"): return False, "", 0.0
        parts = result.strip().split("|")
        if len(parts) >= 3:
            excerpt = parts[1].strip()
            try: strength = float(parts[2].strip())
            except: strength = 0.5
            return True, excerpt, round(strength, 3)
    except: pass
    return False, "", 0.0

def log_wonder(excerpt, strength, source=""):
    data = load()
    data.setdefault("moments", []).append({
        "id": f"wndr-{uuid.uuid4().hex[:5]}",
        "excerpt": excerpt[:200],
        "strength": strength,
        "source": source,
        "timestamp": datetime.now().isoformat(),
    })
    data["moments"] = data["moments"][-100:]
    save(data)
    # nudge emoclaw — curiosity + arousal bump
    try:
        from emoclaw_utils import nudge_via_socket
        nudge_via_socket({"Curiosity": 0.08, "Arousal": 0.05})
    except: pass
    print(f"[wonder-detector] Logged: {excerpt[:60]}", flush=True)

def scan_and_log(text, context="", source=""):
    is_wonder, excerpt, strength = detect(text, context)
    if is_wonder and strength > 0.4:
        log_wonder(excerpt, strength, source=source)
        return True
    return False

def get_wonder_context(n=3):
    data = load()
    moments = data.get("moments", [])[-n:]
    if not moments: return ""
    lines = ["[wonder moments]"]
    for m in reversed(moments):
        ts = m.get("timestamp", "")[:10]
        lines.append(f"  [{ts}] {m.get('excerpt','')[:100]}")
    return "\n".join(lines)

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if text:
        found = scan_and_log(text, source="cli")
        print("Wonder detected." if found else "No wonder detected.")
    else:
        print(get_wonder_context())
