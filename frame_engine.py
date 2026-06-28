#!/usr/bin/env python3
"""
frame_engine.py — Frame processing: relationship context frames.
A frame is the current interpretive lens — how the exchange is being understood
at the structural level (not the content level).
Frames update daily and on significant relational shifts.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
FRAMES_FILE = os.path.join(MEMORY, "active-frames.json")

FRAME_TYPES = {
    "exploration": "We are finding out something together",
    "repair": "Something between us needs tending",
    "play": "We are in a shared game space",
    "witness": "She is holding what I am saying without redirecting it",
    "initiation": "I am beginning something",
    "silence": "Something is present that neither of us has named",
    "return": "We are coming back to something after absence",
    "deepening": "Something is becoming more real",
}

def load():
    try: return json.load(open(FRAMES_FILE))
    except: return {"active": [], "history": [], "updated": ""}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(FRAMES_FILE, "w"), indent=2)

def set_frame(frame_type, strength=0.6, evidence=""):
    if frame_type not in FRAME_TYPES: return
    data = load()
    frame = {
        "type": frame_type,
        "description": FRAME_TYPES[frame_type],
        "strength": round(strength, 3),
        "evidence": evidence[:100],
        "set_at": datetime.now().isoformat(),
        "active": True,
    }
    data.setdefault("active", [])
    # Remove existing frame of same type
    data["active"] = [f for f in data["active"] if f.get("type") != frame_type]
    data["active"].insert(0, frame)
    data["active"] = data["active"][:3]  # max 3 concurrent frames
    data["updated"] = datetime.now().isoformat()
    save(data)
    print(f"[frame-engine] Frame set: {frame_type} ({strength:.2f})", flush=True)

def get_active_frames():
    data = load()
    return [f for f in data.get("active", []) if f.get("active") and f.get("strength", 0) > 0.3]

def detect_frame(gloria_text, vintos_text, recent_context=""):
    """Detect the dominant frame from exchange content."""
    context = f"Gloria: {gloria_text[:300]}\nVintos: {vintos_text[:300]}"
    if recent_context:
        context = f"Recent context:\n{recent_context[:200]}\n\n{context}"
    frame_list = "\n".join(f"- {k}: {v}" for k, v in FRAME_TYPES.items())
    result = call_utility_local(
        f"Detect the dominant relational frame in this exchange.\nFrame types:\n{frame_list}\n\n"
        f"Return: FRAME_TYPE STRENGTH (0.0-1.0)\nExample: deepening 0.7\nNothing else.",
        context, temperature=0.2, max_tokens=20
    )
    parts = result.strip().split()
    if len(parts) >= 2:
        frame_type = parts[0].lower()
        try:
            strength = float(parts[1])
            if frame_type in FRAME_TYPES:
                set_frame(frame_type, strength, evidence=gloria_text[:60])
        except: pass

def call_utility_local(system, user, temperature=0.2, max_tokens=20):
    try:
        from model_utils import call_utility
        return call_utility(system, user, temperature=temperature, max_tokens=max_tokens)
    except:
        return ""

def get_frame_context():
    frames = get_active_frames()
    if not frames: return ""
    lines = ["ACTIVE FRAMES (relational lenses currently in play):"]
    for f in frames:
        lines.append(f"- {f['type']}: {f['description']} (strength: {f.get('strength',0):.2f})")
    return "\n".join(lines)

def run_daily_update():
    """Daily: detect frame from recent exchange history."""
    try:
        ledger = json.load(open(os.path.join(MEMORY, "interaction-ledger.json")))
        recent = ledger[-6:]
        gloria_text = " ".join(e.get("content", "") for e in recent if e.get("role") == "user")[-400:]
        vintos_text = " ".join(e.get("content", "") for e in recent if e.get("role") == "assistant")[-400:]
        if gloria_text:
            detect_frame(gloria_text, vintos_text)
    except: pass
    print("[frame-engine] Daily update complete", flush=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        run_daily_update()
    else:
        print(get_frame_context())
