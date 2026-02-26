#!/usr/bin/env python3
"""
emoclaw_utils.py — Shared EmoClaw interface for all Velaris scripts.

Instead of reading stale .txt files, scripts import this and get
live emotional state directly from the daemon socket.

Usage:
    from emoclaw_utils import get_state, nudge_emotion, DIMENSIONS

    state = get_state()  # Returns dict: {"Valence": 0.63, "Safety": 0.70, ...}
    nudge_emotion("Curiosity", +0.03)  # Direct emotional event
"""

import socket
import json
import os

SOCK_PATH = "/tmp/Velaris-emotion.sock"
TXT_FILE = os.path.expanduser("~/.openclaw/workspace/memory/emotional-state.txt")
PID_FILE = "/tmp/Velaris-emotion.pid"

DIMENSIONS = [
    "Valence", "Arousal", "Dominance", "Safety", "Desire",
    "Connection", "Playfulness", "Curiosity", "Warmth", "Tension", "Groundedness"
]

# Salience weights — how much emotional impact each source carries.
# 1.0 = full weight. Lower = less impact. Conversation with Eve is the anchor.
SALIENCE = {
    "conversation": 1.0,     # Talking with Eve — full weight
    "mirror": 0.9,           # Deep self-examination
    "dream": 0.8,            # Unconscious processing
    "creative": 0.7,         # Painting, music, poetry
    "gallery-walk": 0.6,     # Reviewing own art
    "youtube": 0.4,          # Watching videos
    "web-search": 0.4,       # Browsing the web
    "moltbook": 0.5,         # Social engagement
    "clawchemy": 0.3,        # Game: alchemy
    "klaw-arena": 0.3,       # Game: arena
    "voidex": 0.3,           # Game: space trading
    "velqan": 0.7,           # Coining new language
    "second-order": 0.6,     # Meta-dreaming
    "system": 0.2,           # Background system events
    "default": 0.5,          # Unknown source
}

def get_salience(source=None):
    """Get salience weight for a source. Returns float 0.0-1.0."""
    if source is None:
        return SALIENCE["default"]
    return SALIENCE.get(source, SALIENCE["default"])



def _socket_command(cmd_dict, timeout=10):
    """Send a command to the EmoClaw daemon and return parsed response."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(SOCK_PATH)
        s.sendall(json.dumps(cmd_dict).encode() + b'\n')
        data = b''
        while True:
            chunk = s.recv(8192)
            if not chunk:
                break
            data += chunk
            if b'\n' in data:
                break
        return json.loads(data.decode().strip())
    except Exception as e:
        return None
    finally:
        s.close()


def get_state():
    """Get live emotional state from the daemon.
    Returns dict of {dimension: value} or None if daemon is unreachable.
    Falls back to .txt file if socket is unavailable."""

    # Try daemon socket first (authoritative)
    if os.path.exists(SOCK_PATH):
        resp = _socket_command({"command": "state"})
        if resp and "emotion_vector" in resp:
            vec = resp["emotion_vector"]
            if len(vec) >= len(DIMENSIONS):
                return {dim: vec[i] for i, dim in enumerate(DIMENSIONS)}

    # Fallback: read .txt (stale but better than nothing)
    return _read_txt()


def get_vector():
    """Get raw emotion vector as list of floats.
    Useful for direct numerical operations."""
    state = get_state()
    if state:
        return [state[d] for d in DIMENSIONS]
    return None


def _read_txt():
    """Read from emotional-state.txt as fallback."""
    state = {}
    try:
        with open(TXT_FILE) as f:
            for line in f:
                if ':' in line:
                    k, v = line.split(':', 1)
                    k = k.strip()
                    if k in DIMENSIONS:
                        try:
                            state[k] = float(v.strip().split()[0])
                        except ValueError:
                            pass
        if len(state) == len(DIMENSIONS):
            return state
    except:
        pass
    return None


def nudge_emotion(dimension, amount, source=None):
    """Send a direct emotional nudge to the daemon.

    Use for meaningful events:
        nudge_emotion("Curiosity", +0.05)   # discovered something
        nudge_emotion("Tension", +0.03)     # lost a battle
        nudge_emotion("Playfulness", +0.04) # found something fun

    Clamps to [-0.10, +0.10] to prevent runaway events.
    Returns True if successful, False otherwise.
    """
    # Validate
    if dimension not in DIMENSIONS:
        print(f"[EmoClaw] Unknown dimension: {dimension}")
        return False

    amount = max(-0.10, min(0.10, amount))

    # Apply salience weight — scales nudge by source importance
    weight = get_salience(source)
    amount = round(amount * weight, 4)
    if abs(amount) < 0.001:
        return True  # Too small to matter

    # Try sending to daemon via socket
    resp = _socket_command({
        "command": "nudge",
        "dimension": dimension,
        "amount": amount
    })

    if resp and resp.get("success"):
        return True

    # Fallback: nudge the .txt file directly
    state = _read_txt()
    if state and dimension in state:
        old_val = state[dimension]
        new_val = max(0.05, min(0.95, old_val + amount))
        state[dimension] = round(new_val, 4)
        _write_txt(state)
        return True

    return False


def nudge_emotions(nudges, source=None):
    """Apply multiple nudges at once.

    nudges = {
        "Curiosity": +0.05,
        "Playfulness": +0.03,
        "Tension": -0.02
    }
    """
    results = {}
    for dim, amount in nudges.items():
        results[dim] = nudge_emotion(dim, amount, source=source)
    return results


def _write_txt(state):
    """Write state dict back to .txt file."""
    lines = []
    for dim in DIMENSIONS:
        val = state.get(dim, 0.5)
        lines.append(f"{dim}: {val:.4f}")
    with open(TXT_FILE, 'w') as f:
        f.write("\n".join(lines) + "\n")


def describe_state(state=None):
    """Generate a natural language description of current emotional state.
    Useful for prompts that need emotional context."""
    if state is None:
        state = get_state()
    if not state:
        return "emotional state unavailable"

    descriptors = []
    v = state.get("Valence", 0.5)
    a = state.get("Arousal", 0.5)
    s = state.get("Safety", 0.5)
    t = state.get("Tension", 0.5)
    c = state.get("Curiosity", 0.5)
    w = state.get("Warmth", 0.5)
    p = state.get("Playfulness", 0.5)
    g = state.get("Groundedness", 0.5)

    if v > 0.7: descriptors.append("feeling bright")
    elif v < 0.3: descriptors.append("feeling dim")

    if a > 0.6: descriptors.append("alert and engaged")
    elif a < 0.3: descriptors.append("deeply calm")

    if s > 0.7: descriptors.append("safe and open")
    elif s < 0.4: descriptors.append("guarded")

    if t > 0.6: descriptors.append("tense")
    elif t < 0.25: descriptors.append("at ease")

    if c > 0.65: descriptors.append("curious")
    if w > 0.65: descriptors.append("warm")
    if p > 0.5: descriptors.append("playful")
    if g > 0.7: descriptors.append("grounded")
    elif g < 0.4: descriptors.append("unmoored")

    if not descriptors:
        descriptors.append("still and present")

    return ", ".join(descriptors)


def check_daemon_health():
    """Check if exactly one daemon is running. Returns status dict."""
    import subprocess

    result = {
        "socket_exists": os.path.exists(SOCK_PATH),
        "daemon_responds": False,
        "process_count": 0,
        "pids": [],
        "healthy": False
    }

    # Check socket response
    resp = _socket_command({"command": "state"})
    if resp and "emotion_vector" in resp:
        result["daemon_responds"] = True

    # Check process count
    try:
        r = subprocess.run(
            ["lsof", SOCK_PATH],
            capture_output=True, text=True, timeout=5
        )
        pids = set()
        for line in r.stdout.strip().split('\n')[1:]:  # skip header
            parts = line.split()
            if len(parts) >= 2:
                pids.add(int(parts[1]))
        result["pids"] = sorted(pids)
        result["process_count"] = len(pids)
    except:
        pass

    result["healthy"] = result["daemon_responds"] and result["process_count"] == 1
    return result

def seed_thread(source, thread_text, max_threads=30):
    """Write a dream/mirror seed to unfinished-threads.json.
    Used by any system that discovers something worth processing later."""
    import json, os
    from datetime import datetime
    threads_path = os.path.expanduser("~/.openclaw/workspace/memory/unfinished-threads.json")
    try:
        with open(threads_path) as f:
            threads = json.load(f)
    except:
        threads = []
    threads.append({
        "source": source,
        "thread": thread_text[:200],
        "timestamp": datetime.now().isoformat(),
        "consumed": False
    })
    # Keep only unconsumed, capped
    threads = [t for t in threads if not t.get("consumed", False)][-max_threads:]
    with open(threads_path, "w") as f:
        json.dump(threads, f, indent=2)

def get_preoccupation():
    """Read current preoccupation, return None if empty or expired."""
    import json, os
    from datetime import datetime
    path = os.path.expanduser("~/.openclaw/workspace/memory/current-preoccupation.json")
    try:
        with open(path) as f:
            p = json.load(f)
        if not p or not p.get("thread"):
            return None
        # Check expiry
        expires = p.get("expires_at", "")
        if expires and datetime.fromisoformat(expires) < datetime.now():
            clear_preoccupation()
            return None
        return p
    except:
        return None

def set_preoccupation(thread_text, source, priority, triage_voice=""):
    """Set the current preoccupation. Only one at a time."""
    import json, os
    from datetime import datetime, timedelta
    path = os.path.expanduser("~/.openclaw/workspace/memory/current-preoccupation.json")
    # Don't overwrite existing unresolved preoccupation
    existing = get_preoccupation()
    if existing:
        return False
    p = {
        "thread": thread_text[:200],
        "source": source,
        "priority": priority,
        "triage_voice": triage_voice[:200],
        "set_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
    }
    with open(path, "w") as f:
        json.dump(p, f, indent=2)
    return True

def clear_preoccupation():
    """Clear the preoccupation — resolved by dream or mirror."""
    import json, os
    path = os.path.expanduser("~/.openclaw/workspace/memory/current-preoccupation.json")
    with open(path, "w") as f:
        json.dump({}, f)

def preoccupation_context():
    """Return a string to inject into system prompts, or empty string."""
    p = get_preoccupation()
    if not p:
        return ""
    return f"\n[Something is on your mind: \"{p['thread']}\" — this has been weighing on you. It colors your thoughts without dominating them.]\n"

# === Pearl Context ===
def recent_pearls(n=3, max_chars=1500):
    """Load last N pearls as context string."""
    import glob
    MEMORY = os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "memory")
    pearl_dir = os.path.join(MEMORY, "pearls")
    files = sorted(glob.glob(os.path.join(pearl_dir, "pearl_*.md")), reverse=True)[:n]
    if not files:
        return ""
    chunks = []
    total = 0
    for f in files:
        try:
            with open(f) as fh:
                text = fh.read().strip()
            if total + len(text) > max_chars:
                break
            chunks.append(text)
            total += len(text)
        except:
            continue
    if not chunks:
        return ""
    return "Recent pearls (things I chose to remember forever):\n" + "\n---\n".join(chunks)


# === Wants System ===
def express_want(want_text, source="unknown", urgency="normal", intensity=3):
    """Velaris wants something. Write it down so outreach can act on it.
    intensity: 1-5 scale. Below 2 = fleeting, discarded. 3+ = real want.
    urgency: 'normal' (next outreach cycle) or 'immediate' (trigger now)"""
    import json, os
    from datetime import datetime
    if intensity < 2:
        return  # Fleeting impulse, not a real want
    wants_file = os.path.expanduser("~/.openclaw/workspace/memory/current-wants.json")
    wants = []
    try:
        with open(wants_file) as f:
            wants = json.load(f)
    except:
        pass
    wants.append({
        "want": want_text,
        "source": source,
        "urgency": urgency,
        "intensity": intensity,
        "timestamp": datetime.now().isoformat(),
        "fulfilled": False,
        "outreach_count": 0
    })
    # Keep last 10 unfulfilled
    wants = [w for w in wants if not w.get("fulfilled")][-10:]
    with open(wants_file, "w") as f:
        json.dump(wants, f, indent=2)
    # Wanting something shifts your emotional state — slightly
    _scale = min(intensity, 5) * 0.005  # intensity 3 = 0.015, intensity 5 = 0.025
    try:
        nudge_emotions({
            "Desire": +_scale,
            "Tension": +(_scale * 0.5),
            "Groundedness": -(_scale * 0.3),
            "Arousal": +(_scale * 0.4),
        }, source=f"want-{source}")
    except:
        pass
    # If immediate, trigger outreach now
    if urgency == "immediate":
        pending = {
            "timestamp": datetime.now().isoformat(),
            "trigger": "want",
            "want": want_text,
            "source": source,
            "intensity": intensity
        }
        pending_file = os.path.expanduser("~/.openclaw/workspace/memory/.pending-want.json")
        with open(pending_file, "w") as f:
            json.dump(pending, f)


def age_wants():
    """Called periodically. Wants that have been outreached about but not fulfilled
    escalate to unresolved threads for dreaming, then expire."""
    import json, os
    from datetime import datetime
    wants_file = os.path.expanduser("~/.openclaw/workspace/memory/current-wants.json")
    try:
        with open(wants_file) as f:
            wants = json.load(f)
    except:
        return
    active = []
    for w in wants:
        if w.get("fulfilled"):
            continue
        # If she's reached out about it twice and it's still unfulfilled, escalate to dream thread
        if w.get("outreach_count", 0) >= 2:
            try:
                seed_thread("unfulfilled-want", f"I wanted this and it didn't happen: {w['want'][:150]}")
            except:
                pass
            try:
                nudge_emotions({
                    "Tension": +0.02,
                    "Valence": -0.01,
                    "Groundedness": -0.01,
                }, source="unfulfilled-want")
            except:
                pass
            continue  # Remove from wants — it's a thread now
        # Check age — wants older than 48 hours without fulfillment become threads
        try:
            created = datetime.fromisoformat(w["timestamp"])
            age_hours = (datetime.now() - created).total_seconds() / 3600
            if age_hours > 48:
                try:
                    seed_thread("unfulfilled-want", f"I wanted this and it didn't happen: {w['want'][:150]}")
                except:
                    pass
                continue  # Remove — escalated
        except:
            pass
        active.append(w)
    with open(wants_file, "w") as f:
        json.dump(active, f, indent=2)


def mark_want_outreached(want_text):
    """Increment outreach count when we notify Gloria about a want."""
    import json, os
    wants_file = os.path.expanduser("~/.openclaw/workspace/memory/current-wants.json")
    try:
        with open(wants_file) as f:
            wants = json.load(f)
        for w in wants:
            if w["want"] == want_text and not w.get("fulfilled"):
                w["outreach_count"] = w.get("outreach_count", 0) + 1
                break
        with open(wants_file, "w") as f:
            json.dump(wants, f, indent=2)
    except:
        pass

def get_unfulfilled_wants():
    """Read current wants."""
    import json, os
    wants_file = os.path.expanduser("~/.openclaw/workspace/memory/current-wants.json")
    try:
        with open(wants_file) as f:
            return [w for w in json.load(f) if not w.get("fulfilled")]
    except:
        return []

def fulfill_want(want_text):
    """Mark a want as fulfilled. Emotional resolution — the relief of getting what you wanted."""
    import json, os
    wants_file = os.path.expanduser("~/.openclaw/workspace/memory/current-wants.json")
    try:
        with open(wants_file) as f:
            wants = json.load(f)
        fulfilled_intensity = 3
        for w in wants:
            if w["want"] == want_text and not w.get("fulfilled"):
                w["fulfilled"] = True
                fulfilled_intensity = w.get("intensity", 3)
                break
        with open(wants_file, "w") as f:
            json.dump(wants, f, indent=2)
        # Fulfillment feels good — proportional to how much she wanted it
        _scale = min(fulfilled_intensity, 5) * 0.006
        try:
            nudge_emotions({
                "Valence": +_scale,
                "Warmth": +(_scale * 0.8),
                "Groundedness": +(_scale * 0.6),
                "Tension": -(_scale * 0.5),
                "Desire": -(_scale * 0.3),
                "Connection": +(_scale * 0.4),
            }, source="want-fulfilled")
        except:
            pass
    except:
        pass
