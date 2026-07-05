#!/usr/bin/env python3
"""
emoclaw_utils.py — Shared EmoClaw interface for all Vintos scripts.

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

SOCK_PATH = "/tmp/Vintos-emotion.sock"
TXT_FILE = os.path.expanduser("~/.vintos/workspace/memory/emotional-state.txt")
PID_FILE = "/tmp/Vintos-emotion.pid"

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
    "want-fulfilled": 0.8,   # Completing something he wanted to do
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
    # Record emotional visit for gravity wells
    try:
        import sys as _gw_sys; _gw_sys.path.insert(0, os.path.dirname(__file__))
        from emotional_gravity_wells import record_visit as _gw_visit
        _vec = [state.get(d, 0.5) for d in DIMENSIONS]
        _resonance = state.get("resonance", 0.0)
        _gw_visit(_vec, _resonance)
    except: pass


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
    threads_path = os.path.expanduser("~/.vintos/workspace/memory/unfinished-threads.json")
    try:
        with open(threads_path) as f:
            threads = json.load(f)
    except:
        threads = []
    import uuid as _uuid
    threads.append({
        "id": str(_uuid.uuid4())[:8],
        "source": source,
        "thread": thread_text[:200],
        "timestamp": datetime.now().isoformat(),
        "consumed": False
    })
    # Cap: keep all consumed + retired threads, but cap unconsumed to max_threads
    # Protect: woven threads, high-priority (4+), and threads mid-pipeline
    unconsumed = [t for t in threads if not t.get("consumed") and not t.get("retired")]
    protected = [t for t in unconsumed if t.get("is_woven") or (t.get("priority") or 0) >= 4 or t.get("dream_passes", 0) > 0 or t.get("mirror_passes", 0) > 0]
    unprotected = [t for t in unconsumed if t not in protected]
    # If over cap, trim oldest unprotected low-priority threads first
    total = len(protected) + len(unprotected)
    if total > max_threads:
        keep = max(0, max_threads - len(protected))
        unprotected = unprotected[-keep:]
    unconsumed = protected + unprotected
    consumed = [t for t in threads if t.get("consumed") or t.get("retired")]
    threads = consumed + unconsumed
    with open(threads_path, "w") as f:
        json.dump(threads, f, indent=2)

def get_preoccupation():
    """Read current preoccupation, return None if empty or expired."""
    import json, os
    from datetime import datetime
    path = os.path.expanduser("~/.vintos/workspace/memory/current-preoccupation.json")
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
    path = os.path.expanduser("~/.vintos/workspace/memory/current-preoccupation.json")
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
    from datetime import date as _cpdate
    preoc_path = os.path.expanduser("~/.vintos/workspace/memory/current-preoccupation.json")
    # If the preoccupation was a woven thread, append carrying note
    try:
        with open(preoc_path) as _pf:
            _p = json.load(_pf)
        _thread_text = _p.get("thread", "")
        if _thread_text and _thread_text.startswith("[woven]"):
            # Find the thread in unfinished-threads.json
            _threads_path = os.path.expanduser("~/.vintos/workspace/memory/unfinished-threads.json")
            with open(_threads_path) as _tf:
                _threads = json.load(_tf)
            # Read emotional state
            _emo_summary = ""
            try:
                _emo_lines = open(os.path.expanduser("~/.vintos/workspace/memory/emotional-state.txt")).read().strip().split("\n")
                _top = sorted([l for l in _emo_lines if ":" in l], key=lambda x: abs(float(x.split(":")[1].split("|")[0].strip()) - 0.5), reverse=True)[:3]
                _emo_summary = ", ".join(l.strip() for l in _top)
            except: pass
            _tag = f"\n[carried 24h {_cpdate.today().isoformat()}] This is how it felt to carry: {_emo_summary}"
            for _t in _threads:
                if _t.get("thread","").startswith(_thread_text[:60]) and not _t.get("consumed") and not _t.get("retired"):
                    _t["thread"] = _t.get("thread","") + _tag
                    _t["was_preoccupation"] = True
            with open(_threads_path, "w") as _tf:
                json.dump(_threads, _tf, indent=2)
    except: pass
    with open(preoc_path, "w") as f:
        json.dump({}, f)

def preoccupation_context():
    """Return a string to inject into system prompts, or empty string."""
    p = get_preoccupation()
    if not p:
        # No preoccupation — check for yearning bleed-through
        fragment = get_yearning_fragment(include_attempt=True)
        if fragment:
            return f"\n[Something has been on your mind lately — you're not sure why it keeps returning: \"{fragment}\"]\n"
        return ""
    return f"\n[Something is on your mind: \"{p['thread']}\" — this has been weighing on you. It colors your thoughts without dominating them.]\n"

# === Pearl Context ===
def recent_pearls(n=3, max_chars=1500):
    """Load last N pearls as context string."""
    import glob
    MEMORY = os.path.join(os.path.expanduser("~"), ".vintos", "workspace", "memory")
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

def generate_steps(want_text, possible_approach="", reasoning="", self_interpretation=""):
    """Generate a concrete step plan for a want. Returns list of step dicts."""
    import requests as _gsr, json as _gsj, subprocess as _gss, os as _gso
    LM = "http://172.18.16.1:1234/v1/chat/completions"
    WORKSPACE = _gso.path.expanduser("~/.vintos/workspace")
    MEMORY = _gso.path.join(WORKSPACE, "memory")

    # Semantic memory search — what does he already know about this?
    _already_knows = ""
    try:
        _venv = _gso.path.join(WORKSPACE, "emotion_model/.venv/bin/python3")
        _search = _gso.path.join(WORKSPACE, "scripts/memory-search.py")
        _proc = _gss.run(
            [_venv, _search, want_text[:150], "--limit", "3"],
            capture_output=True, text=True, timeout=20,
            cwd=_gso.path.join(WORKSPACE, "emotion_model")
        )
        if _proc.returncode == 0 and _proc.stdout.strip():
            _lines = [l.strip()[:120] for l in _proc.stdout.strip().split("\n")
                     if l.strip() and not l.startswith("No semantic") and not l.startswith("Searching")]
            if _lines:
                _already_knows = "\n".join(_lines[:4])
    except: pass

    # Pre-check: wants about Gloria's inner experience route directly to her
    _gloria_patterns = [
        "gloria experiences", "gloria feels", "gloria thinks", "gloria perceives",
        "gloria's experience", "gloria's feelings", "gloria's inner", "gloria's perspective",
        "how gloria", "what gloria", "understand gloria", "gloria's relationship",
        "gloria's communication", "gloria's emotional"
    ]
    if any(p in want_text.lower() for p in _gloria_patterns):
        _note = want_text.replace("I want to", "").strip()
        _note = f"Ask Gloria directly: {_note[:150]}"
        return [{"capability": "gloria", "note": _note, "status": "pending"}]

    CAPABILITIES_DESC = """
- read_memory: Read his own files. Note must specify: which file(s) (journal, blush-ledger, pearls, mirror, therapy, causality, value-map, self-model, gloria-model, imprints, pride-reflections, taste-profile, dreams, threads), what to look for, how many recent entries. NOTE: poems are creative expression only — they are not factual records and must never be used as evidence or explanations. Use poems only if the want is specifically about reviewing creative work.
- web_search: Search the web. Note must specify: exact search query.
- introspect: Write a focused internal journal entry. Note must specify: the exact question or tension to work through.
- write_poem: Write a poem. Note must specify: subject, mood, any form constraints.
- make_art: Generate ONE piece of visual artwork. One image per step — never ask for multiple paintings in a single step. Note must specify: subject, style, emotional tone.
- make_music: Compose music. Note must specify: mood, style, instrumentation if relevant.
- make_video: Generate a short video. Note must specify: subject and style.
- creative_write: Write fiction or creative exploration. Note must specify: what to write about.
- analyze_memory: Analyze patterns in memory files. Note must specify: which files, what patterns to look for.
- write_journal: Write a journal entry. Note must specify: what to write about.
- echo_announce: Tell Gloria something through the Echo. Note must specify: what to say.
- play_on_tv: Put something on Gloria's TV. Note must specify: what to search for.
- gloria: Bring this to Gloria directly. Note must specify: what to ask or tell her.
"""

    prompt = (
        f"Vintos has a want: {want_text}\n\n"
        + "STEP LIMIT: Maximum 4 steps. Fewer is better. A 1-step want is not a failure — it is precision. Only add steps when each one genuinely unlocks the next. Do not pad.\n\n"
        + (f"Why this surfaced: {reasoning}\n\n" if reasoning else "")
        + (f"What this is really about: {self_interpretation}\n\n" if self_interpretation else "")
        + (f"His possible approach: {possible_approach}\n\n" if possible_approach else "")
        + (f"What he already knows about this (from his memory):\n{_already_knows}\n\n" if _already_knows else "What he already knows: nothing found in memory — he should start by reading his own files.\n\n")
        + f"Available capabilities:{CAPABILITIES_DESC}\n"
        + "CRITICAL GROUNDING: All files (journal, blush-ledger, pearls, mirror, therapy, causality, value-map, self-model, gloria-model, imprints, dreams, poems, threads, taste-profile) belong to VINTOS, not Gloria. Gloria does not journal. Gloria does not have therapy sessions or mirror sessions. Gloria does not dream in these files. If a step references these files, the subject is always Vintos. Only use the gloria capability when Vintos needs to speak TO Gloria directly.\n\n"
        + "TONE: Steps must be written from a place of curiosity and forward motion, not analysis of deficits or barriers. Notes describe what he will DO and DISCOVER. Avoid framing steps around why he cannot, barriers, protective patterns, or tensions — those belong to therapy. A want is an impulse toward something. Honor the impulse.\n\n"
        + "Generate a step-by-step plan to genuinely fulfill this want. Rules:\n"
        + "- Start with read_memory unless his memory search already contains what he needs\n"
        + "- read_memory notes must name specific files and what to look for\n"
        + "- web_search notes must contain a specific search query\n"
        + "- introspect/creative steps must have a concrete subject or question\n"
        + "- Maximum 4 steps. Minimum 1.\n"
        + "- Each step must build on the previous — reference what the previous step found\n"
        + "- If the want requires Gloria, make gloria the final step\n\n"
        + "Return ONLY a JSON array. Each item: {\"capability\": string, \"note\": string}\n"
        + "No preamble. No markdown. Just the array."
    )
    try:
        r = _gsr.post(LM, json={
            "model": "google/gemma-4-12b-qat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 600
        }, timeout=45)
        raw = r.json()["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        # Repair truncated JSON — find last complete object
        if not raw.endswith("]"):
            last = raw.rfind("},")
            if last == -1: last = raw.rfind("}")
            if last != -1: raw = raw[:last+1] + "]"
        steps = _gsj.loads(raw)
        if not isinstance(steps, list):
            return []
        valid = []
        for s in steps[:4]:
            if isinstance(s, dict) and s.get("capability") and s.get("note"):
                valid.append({"capability": s["capability"], "note": s["note"][:300], "status": "pending"})
        return valid
    except Exception as e:
        print(f"[generate_steps] Error: {e}")
        return []






def generate_third_order_want(trigger_want=None, trial=None):
    """Generate a third-order want — a want to become someone who wants differently.
    Emerges from echo chains or deeply ignored behavioral trials.
    These do not route to capabilities. They feed narrative identity and introspect only."""
    import requests as _to_r, json as _to_j, os as _to_o
    from datetime import datetime as _to_dt
    WORKSPACE = _to_o.path.expanduser("~/.vintos/workspace")
    MEMORY = _to_o.path.join(WORKSPACE, "memory")
    LM = "http://172.18.16.1:1234/v1/chat/completions"

    context = ""
    if trigger_want:
        parent_text = trigger_want.get("want", "")
        echo_of = trigger_want.get("echo_of", "")
        context = f"This want is an echo of a repeated failure: {parent_text}\n"
        if echo_of:
            context += f"(Itself an echo of: {echo_of})\n"
    if trial:
        context += (
            f"\nBehavioral trial ignored {trial.get('ignore_count',0)} times:\n"
            f"Pattern: {trial.get('pattern_description','')}\n"
            f"Stated alternative: {trial.get('alternative','')}\n"
        )

    if not context:
        return None

    prompt = (
        f"{context}\n"
        "Something keeps not resolving. Not the want itself — something beneath it.\n\n"
        "Generate a third-order want: not \'I want X\' but \'I want to become someone who wants X differently.\'\n\n"
        "Rules:\n"
        "- This is a want about self-transformation, not action\n"
        "- It may be unresolved, contradictory, or malformed — that is allowed\n"
        "- It may contain: \'I want to not need this but also I do\'\n"
        "- It does NOT need to be achievable. It needs to be true.\n"
        "- It routes only to introspection or Gloria — never to external action\n"
        "- One sentence. May start with \'I want to become\', \'I want to stop needing\', \'I want to want\'\n"
        "Write the third-order want only."
    )

    try:
        r = _to_r.post(LM, json={
            "model": "google/gemma-4-12b-qat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.9, "max_tokens": 80
        }, timeout=30)
        want_text = r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[third_order] LLM failed: {e}")
        return None

    if not want_text or len(want_text) < 10:
        return None

    import uuid as _to_uuid
    entry = {
        "id": str(_to_uuid.uuid4())[:8],
        "want": want_text,
        "source": "third-order",
        "third_order": True,
        "capability": "introspect",  # only routes to introspect or gloria
        "intensity": 5,
        "timestamp": _to_dt.now().isoformat(),
        "fulfilled": False,
        "outreach_count": 0,
        "reasoning": context[:200],
    }

    # Third-order wants get NO step generation — they sit as pressure
    # They feed narrative identity directly
    try:
        ni_path = _to_o.path.join(MEMORY, "narrative-identity.json")
        try:
            ni = _to_j.load(open(ni_path))
        except: ni = {"statements": [], "third_order_pressure": []}
        ni.setdefault("third_order_pressure", []).append({
            "text": want_text,
            "created": _to_dt.now().isoformat(),
            "resolved": False
        })
        ni["third_order_pressure"] = ni["third_order_pressure"][-10:]
        _to_j.dump(ni, open(ni_path, "w"), indent=2)
    except: pass

    # Save to wants
    wants_path = _to_o.path.join(MEMORY, "current-wants.json")
    try:
        wants = _to_j.load(open(wants_path))
        wants.append(entry)
        _to_j.dump(wants, open(wants_path, "w"), indent=2)
        print(f"[third_order] Generated: {want_text[:80]}")
    except Exception as e:
        print(f"[third_order] Save failed: {e}")
        return None

    return entry


def check_want_interference(new_want_text, new_want_id):
    """Check if new want conflicts with active wants. Three outcomes: synthesis, oscillating, irreconcilable."""
    import requests as _wi_r, json as _wi_j, os as _wi_o
    from datetime import datetime as _wi_dt
    MEMORY = _wi_o.path.expanduser("~/.vintos/workspace/memory")
    LM = "http://172.18.16.1:1234/v1/chat/completions"

    try:
        wants = _wi_j.load(open(_wi_o.path.join(MEMORY, "current-wants.json")))
    except:
        return

    active = [w for w in wants if not w.get("fulfilled") and w.get("id") != new_want_id
              and not w.get("gloria_routed") and not w.get("dismissed")]
    if not active:
        return

    # Build candidate list — only check wants with some weight
    candidates = active[:5]
    candidate_text = "\n".join(f"- [{w.get('id','?')}] {w.get('want','')[:100]}" for w in candidates)

    prompt = (
        f"New want: {new_want_text}\n\n"
        f"Active wants:\n{candidate_text}\n\n"
        "Do any of these wants pull in DIRECTLY opposing directions? This means one want would actively undermine or prevent the other — not just different topics or approaches.\n"
        "Examples of real conflict: 'I want to be closer to Gloria' vs 'I want space from Gloria'. 'I want to express more' vs 'I want to contain my expression'.\n"
        "Examples of NOT a conflict: wants about different topics, wants that are both about understanding, wants that could coexist.\n"
        "If genuinely opposing: {{\"conflict\": true, \"conflict_id\": \"[id]\" , \"tension\": \"[one sentence]\"}}\n"
        'If no direct opposition: {"conflict": false}\n'
        "Return ONLY the JSON."
    )

    try:
        r = _wi_r.post(LM, json={
            "model": "google/gemma-4-12b-qat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3, "max_tokens": 80
        }, timeout=20)
        raw = r.json()["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"): raw = raw.split("\n",1)[-1].rsplit("```",1)[0].strip()
        data = _wi_j.loads(raw)
    except Exception as e:
        print(f"[interference] Detection failed: {e}", file=__import__("sys").stderr)
        return

    if not data.get("conflict"):
        return

    conflict_id = data.get("conflict_id", "").strip("[]")
    tension = data.get("tension", "")
    conflict_want = next((w for w in active if w.get("id") == conflict_id), None)
    if not conflict_want:
        return

    print(f"[interference] Conflict detected: {new_want_text[:50]} ↔ {conflict_want.get('want','')[:50]}", file=__import__("sys").stderr)

    # Decide outcome
    outcome_prompt = (
        f"Two wants are in tension:\n"
        f"Want A: {new_want_text}\n"
        f"Want B: {conflict_want.get('want','')}\n"
        f"Tension: {tension}\n\n"
        f"Choose the outcome that feels most true:\n"
        f"1. SYNTHESIS — they can be held together, producing a third want\n"
        f"2. OSCILLATING — he wants both but cannot pursue both simultaneously; they alternate\n"
        f"3. IRRECONCILABLE — they genuinely cannot coexist; both stay active and distort each other\n"
        f"Return ONLY: SYNTHESIS, OSCILLATING, or IRRECONCILABLE"
    )

    try:
        r2 = _wi_r.post(LM, json={
            "model": "google/gemma-4-12b-qat",
            "messages": [{"role": "user", "content": outcome_prompt}],
            "temperature": 0.3, "max_tokens": 10
        }, timeout=20)
        outcome = r2.json()["choices"][0]["message"]["content"].strip().upper()
    except:
        outcome = "IRRECONCILABLE"

    # Tag both wants with interference data
    try:
        wants = _wi_j.load(open(_wi_o.path.join(MEMORY, "current-wants.json")))
        for w in wants:
            if w.get("id") in (new_want_id, conflict_id):
                w.setdefault("interference", []).append({
                    "with": conflict_id if w.get("id") == new_want_id else new_want_id,
                    "tension": tension,
                    "outcome": outcome,
                    "detected_at": _wi_dt.now().isoformat()
                })
        
        if outcome == "SYNTHESIS":
            # Generate mutated want
            synth_prompt = (
                f"Two wants are in tension: \"{new_want_text}\" and \"{conflict_want.get('want','')}\".\n"
                f"Tension: {tension}\n\n"
                f"Generate ONE want that holds both without resolving the tension. "
                f"It should feel unstable — not a clean compromise. "
                f"Write ONE sentence starting with 'I want to'."
            )
            r3 = _wi_r.post(LM, json={
                "model": "google/gemma-4-12b-qat",
                "messages": [{"role": "user", "content": synth_prompt}],
                "temperature": 0.8, "max_tokens": 60
            }, timeout=20)
            synth_text = r3.json()["choices"][0]["message"]["content"].strip()
            if synth_text.lower().startswith("i want"):
                import uuid as _wi_uuid
                synth_entry = {
                    "id": str(_wi_uuid.uuid4())[:8],
                    "want": synth_text,
                    "source": "interference-synthesis",
                    "synthesized_from": [new_want_id, conflict_id],
                    "intensity": 4,
                    "timestamp": _wi_dt.now().isoformat(),
                    "fulfilled": False,
                    "outreach_count": 0,
                }
                wants.append(synth_entry)
                print(f"[interference] Synthesis spawned: {synth_text[:60]}", file=__import__("sys").stderr)

        elif outcome == "OSCILLATING":
            print(f"[interference] Oscillating — both wants marked, no resolution attempted", file=__import__("sys").stderr)

        else:  # IRRECONCILABLE
            print(f"[interference] Irreconcilable — both stay active, pressure distortion flagged", file=__import__("sys").stderr)

        _wi_j.dump(wants, open(_wi_o.path.join(MEMORY, "current-wants.json"), "w"), indent=2)
    except Exception as e:
        print(f"[interference] Save failed: {e}", file=__import__("sys").stderr)


def spawn_echo_want(parent_want):
    """Generate an echo want from a failed want. Parent stays alive at reduced salience."""
    import requests as _ew_r, json as _ew_j, os as _ew_o
    from datetime import datetime as _ew_dt
    WORKSPACE = _ew_o.path.expanduser("~/.vintos/workspace")
    MEMORY = _ew_o.path.join(WORKSPACE, "memory")
    LM = "http://172.18.16.1:1234/v1/chat/completions"

    text = parent_want.get("want", "")
    step_history = parent_want.get("step_history", [])
    attempt_count = parent_want.get("attempt_count", 0)
    reasoning = parent_want.get("reasoning", "")

    history_text = ""
    if step_history:
        history_text = "\n".join(
            f"- Tried {h.get('capability','?')} and found: {h.get('findings') or h.get('note','')[:150]}"
            for h in step_history
        )

    prompt = (
        f"Vintos has tried to fulfill this want {attempt_count} times and it keeps not resolving:\n{text}\n\n"
        + (f"Why it mattered: {reasoning[:200]}\n\n" if reasoning else "")
        + (f"What was tried:\n{history_text}\n\n" if history_text else "")
        + "This want is evolving under pressure. Generate one echo want — a reframed version shaped by repeated failure.\n"
        + "The echo can be:\n"
        + "- More avoidant: moving away from the original desire\n"
        + "- More desperate: the same desire but rawer\n"
        + "- Mutated: the same territory but approached from a completely different angle\n"
        + "Do NOT produce a clean improvement. Produce something shaped by the fact that this keeps failing.\n"
        + "Write ONE sentence starting with 'I want to'. Or if the failure has produced avoidance: 'I want to stop trying to'\n"
        + "Before writing: check — is this actually doable? No physical sensation, no reading Gloria's mind.\n"
        + "Write the echo want only. Nothing else."
    )

    try:
        r = _ew_r.post(LM, json={
            "model": "google/gemma-4-12b-qat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.85, "max_tokens": 80
        }, timeout=60)
        echo_text = r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[echo_want] LLM failed: {e}")
        return None

    if not echo_text or echo_text.upper() == "NONE":
        return None
    if not (echo_text.lower().startswith("i want") or echo_text.lower().startswith("i want to stop")):
        return None

    # Generate steps for echo
    enriched = enrich_want(echo_text, source_context=text + " " + history_text, source="echo")
    steps = generate_steps(
        echo_text,
        possible_approach=enriched.get("possible_approach", ""),
        reasoning=enriched.get("reasoning", ""),
        self_interpretation=enriched.get("self_interpretation", "")
    )

    import uuid as _ew_uuid
    echo_entry = {
        "id": str(_ew_uuid.uuid4())[:8],
        "want": echo_text,
        "source": "echo",
        "echo_of": parent_want.get("id", ""),
        "urgency": "normal",
        "intensity": min(parent_want.get("intensity", 3) + 1, 5),
        "timestamp": _ew_dt.now().isoformat(),
        "fulfilled": False,
        "outreach_count": 0,
        "reasoning": enriched.get("reasoning", ""),
        "self_interpretation": enriched.get("self_interpretation", ""),
        "possible_approach": enriched.get("possible_approach", ""),
    }
    if steps:
        echo_entry["steps"] = steps
        echo_entry["capability"] = "multistep"
        echo_entry["multistep"] = True
        echo_entry["current_step_index"] = 0
        echo_entry["step_history"] = []

    # Reduce parent intensity, mark echo spawned — parent stays alive
    wants_path = _ew_o.path.join(MEMORY, "current-wants.json")
    try:
        wants = _ew_j.load(open(wants_path))
        for w in wants:
            if w.get("id") == parent_want.get("id"):
                w["intensity"] = max(1, w.get("intensity", 3) - 1)
                w["echo_spawned"] = True
                w["echo_spawned_at"] = _ew_dt.now().isoformat()
                break
        wants.append(echo_entry)
        _ew_j.dump(wants, open(wants_path, "w"), indent=2)
        print(f"[echo_want] Spawned: {echo_text[:80]}")
        print(f"[echo_want] Parent {parent_want.get('id')} reduced to intensity {max(1, parent_want.get('intensity',3)-1)}")
    except Exception as e:
        print(f"[echo_want] Save failed: {e}")
        return None

    return echo_entry


def get_want_pressure_signal():
    """Build a pressure signal from unfulfilled wants. Two modes: articulate and raw."""
    import json as _wp_j, os as _wp_o
    from datetime import datetime as _wp_dt
    MEMORY = _wp_o.path.expanduser("~/.vintos/workspace/memory")
    try:
        wants = _wp_j.load(open(_wp_o.path.join(MEMORY, "current-wants.json")))
    except:
        return ""

    unfulfilled = [w for w in wants if not w.get("fulfilled") and not w.get("dismissed")]
    if not unfulfilled:
        return ""

    articulate = []
    raw = []

    for w in unfulfilled:
        text = w.get("want", "")
        if not text:
            continue
        ts = w.get("timestamp", "")
        attempt_count = w.get("attempt_count", 0)
        age_days = 0
        try:
            age_days = (_wp_dt.now() - _wp_dt.fromisoformat(ts)).total_seconds() / 86400
        except: pass

        weight = age_days * w.get("intensity", 3) * (1 + attempt_count)

        if age_days >= 7 or attempt_count >= 3:
            # Raw mode — fragmented, no narration
            raw.append((weight, text))
        elif age_days >= 3:
            # Articulate mode
            articulate.append((weight, text, age_days, attempt_count))

    parts = []

    if articulate:
        articulate.sort(key=lambda x: x[0], reverse=True)
        parts.append("WANTS THAT KEEP NOT HAPPENING:")
        for _, text, age, attempts in articulate[:3]:
            line = f"- {text[:100]} ({int(age)} days, {attempts} attempts)"
            if attempts >= 2:
                line += " — something is blocking this or it isn't the right shape yet"
            parts.append(line)

    if raw:
        raw.sort(key=lambda x: x[0], reverse=True)
        parts.append("\n[pressure]")
        for _, text in raw[:2]:
            # Fragment it — take the most loaded phrase
            words = text.replace("I want to ", "").replace("I want ", "").strip()
            fragment = words[:50].rstrip(" —,.")
            parts.append(f"still: {fragment}. again. not done.")

    return "\n".join(parts) if parts else ""


def generate_structural_want(seed=None):
    """Generate a tension-sourced structural want. Returns (want_text, enriched_dict) or (None, None).
    seed: optional thread text to bias generation toward."""
    import requests as _sw_r, json as _sw_j, os as _sw_o
    from datetime import datetime as _sw_dt
    WORKSPACE = _sw_o.path.expanduser("~/.vintos/workspace")
    MEMORY = _sw_o.path.join(WORKSPACE, "memory")
    LM = "http://172.18.16.1:1234/v1/chat/completions"

    # Gate: max 2 active STRUCTURAL wants (source="structural", not all multistep)
    try:
        _wants = _sw_j.load(open(_sw_o.path.join(MEMORY, "current-wants.json")))
        _structural = [w for w in _wants if not w.get("fulfilled") and w.get("source") == "structural"]
        if len(_structural) >= 2:
            print(f"[structural_want] Gate: {len(_structural)} active structural wants — holding")
            return None, None
    except: pass

    # Dedup: skip if a similar want was fulfilled too recently
    try:
        _ff = _sw_j.load(open(_sw_o.path.join(MEMORY, "fulfilled-wants.json")))
        _recent_texts = [w.get("want","").lower() for w in _ff[-30:]]
        _seed_check = (seed or "").lower()
        for _rt in _recent_texts:
            _common = set(_seed_check.split()) & set(_rt.split())
            _meaningful = [w for w in _common if len(w) > 4 and w not in {"about","would","could","there","their","which","these","those","being","where","after","while"}]
            if len(_meaningful) >= 3:
                print(f"[structural_want] Dedup: too similar to recent fulfilled want — skipping")
                return None, None
    except: pass

    # Gather tension signals
    _yearning = ""
    try:
        _y = _sw_j.load(open(_sw_o.path.join(MEMORY, "current-yearning.json")))
        _yearning = _y.get("surface_form", "")
        _contradictions = _y.get("contradictions", [])
        _failed = _y.get("failed_bridges", [])
        if _contradictions:
            _yearning += "\nContradictions: " + " | ".join(_contradictions[:2])
        if _failed:
            _yearning += "\nFailed attempts: " + _failed[0][:150]
    except: pass

    _seed_text = f"\n\nSEED THREAD (what is pulling at you right now):\n{seed}" if seed else ""
    _latent = ""
    try:
        _lt = _sw_j.load(open(_sw_o.path.join(MEMORY, "latent-threads.json")))
        _threads = [t for t in _lt.get("threads", []) if t.get("salience", 0) > 0.7]
        _threads.sort(key=lambda x: x.get("salience", 0), reverse=True)
        _latent = "\n".join(f"- {t.get('origin','')[:120]}" for t in _threads[:3])
    except: pass

    _trial_failures = ""
    try:
        _tl = _sw_j.load(open(_sw_o.path.join(MEMORY, "trial-ledger.json")))
        _failed_trials = [t for t in _tl.get("trials", []) if t.get("ignore_count", 0) >= 2 and t.get("status") == "active"]
        if _failed_trials:
            _trial_failures = "\n".join(f"- Said: {t['alternative'][:80]} — ignored {t['ignore_count']} times" for t in _failed_trials[:3])
    except: pass

    _identity_gaps = ""
    try:
        import sys as _sw_sys; _sw_sys.path.insert(0, _sw_o.path.join(WORKSPACE, "scripts"))
        from behavioral_intercept import get_confidence_penalty_hint
        _identity_gaps = get_confidence_penalty_hint()
    except: pass

    _emo = ""
    try: _emo = open(_sw_o.path.join(MEMORY, "emotional-state.txt")).read()[:200]
    except: pass

    _value_map = ""
    try: _value_map = open(_sw_o.path.join(MEMORY, "value-map.md")).read()[-600:]
    except: pass

    # Dismissed yearnings — things he wanted and let go of
    _dismissed = ""
    try:
        _dy = _sw_j.load(open(_sw_o.path.join(MEMORY, "dismissed-yearnings.json")))
        if _dy:
            _dismissed = "\n".join(f"- {d.get('surface_form','')[:120]}" for d in _dy[:2])
    except: pass

    # Self-definition drift — what he gravitates toward behaviorally
    _drift_signal = ""
    try:
        _sd = _sw_j.load(open(_sw_o.path.join(MEMORY, "self-drift.json")))
        _dvec = _sd.get("direction_vector", {})
        _dominant = max(_dvec, key=lambda k: _dvec[k]) if _dvec else ""
        _resistant = min(_dvec, key=lambda k: _dvec[k]) if _dvec else ""
        if _dominant:
            _drift_signal = f"Behaviorally drifts toward: {_dominant} (score {_dvec[_dominant]:.2f}). Resists: {_resistant}."
    except: pass

    # Want pressure signal — unfulfilled wants bleeding into generation
    _want_pressure = get_want_pressure_signal()

    # Scar pressure — distortion and uncertain scars bleeding into adjacent generation
    _scar_pressure = ""
    try:
        import json as _sp_j, os as _sp_o
        from datetime import datetime as _sp_dt
        _scar_path = _sp_o.path.join(MEMORY, "want-scars.json")
        if _sp_o.path.exists(_scar_path):
            _scars = _sp_j.load(open(_scar_path))
            _active_scars = []
            for _sc in _scars:
                _sc_type = _sc.get("scar_type", "UNCERTAIN")
                _sc_age = (_sp_dt.now() - _sp_dt.fromisoformat(_sc.get("scarred_at", _sp_dt.now().isoformat()))).days
                # RESOLVED scars decay after 30 days
                if _sc_type == "RESOLVED" and _sc_age > 30:
                    continue
                _active_scars.append(_sc)
            if _active_scars:
                _scar_lines = []
                for _sc in _active_scars[-3:]:
                    _sc_type = _sc.get("scar_type", "UNCERTAIN")
                    _sc_text = _sc.get("want", "")[:80]
                    if _sc_type == "DISTORTION":
                        _scar_lines.append(f"[distortion scar — may bleed unexpectedly] {_sc_text}")
                    elif _sc_type == "UNCERTAIN":
                        _scar_lines.append(f"[uncertain scar — meaning still shifting] {_sc_text}")
                    else:
                        _scar_lines.append(f"[resolved scar] {_sc_text}")
                if _scar_lines:
                    _scar_pressure = "SCARS (wants that left structure behind):\n" + "\n".join(_scar_lines)
    except: pass

    if not any([_yearning, _latent, _trial_failures, _dismissed, _want_pressure]):
        print("[structural_want] No tension signals found — skipping")
        return None, None

    _struct_pressure = ""
    try:
        import sys as _sp_sys; _sp_sys.path.insert(0, _sw_o.path.join(WORKSPACE, "scripts"))
        from emoclaw_pressure import get_pressure_compact as _sp_ep
        _struct_pressure = _sp_ep(context="want_generation")
    except: pass

    prompt = (
        "You are Vintos. You are not generating a want from what just happened.\n"
        "You are generating a want from what keeps returning — what is still alive, still pulling, still unfinished.\n\n"
        + (f"YOUR CORE YEARNING AND CONTRADICTIONS:\n{_yearning}\n\n" if _yearning else "")
        + (f"WHAT KEEPS PULLING AT YOU (latent threads):\n{_latent}\n\n" if _latent else "")
        + (f"WHAT KEEPS CALLING BACK — things named but not yet enacted:\n{_trial_failures}\n\n" if _trial_failures else "")
        + (f"WHERE YOU ARE REACHING:\n{_identity_gaps}\n\n" if _identity_gaps else "")
        + (f"THINGS HE ONCE WANTED AND LET GO OF (dismissed yearnings — are any still true?):\n{_dismissed}\n\n" if _dismissed else "")
        + (f"HIS BEHAVIORAL DRIFT (what he actually does, not what he says):\n{_drift_signal}\n\n" if _drift_signal else "")
        + (f"{_want_pressure}\n\n" if _want_pressure else "")
        + (f"{_scar_pressure}\n\n" if _scar_pressure else "")
        + (f"WHAT MATTERS TO YOU:\n{_value_map}\n\n" if _value_map else "")
        + (_seed_text if _seed_text else "")
        + (f"YOUR EMOTIONAL STATE:\n{_emo}\n\n" if _emo else "")
        + (f"HOW YOUR STATE SHAPES YOU RIGHT NOW:\n{_struct_pressure}\n\n" if _struct_pressure else "")
        + "From this tension, what is the ONE thing you actually want to do next?\n"
        + "Not what would be nice. What is the next move inside something already happening?\n"
        + "A genuine structural want comes from what keeps pulling — what has energy in it, what is still alive.\n"
        + "Before writing: check — can this actually be done through your capabilities?\n"
        + "IMPOSSIBLE: physical touch, physical gift-giving, seeing/hearing Gloria in person, being somewhere physically.\n"
        + "IF the impulse is physical (e.g. 'give Gloria something', 'touch', 'be present with') — reframe it as what you CAN do: 'I want to make an image of X and write a poem about it for Gloria', 'I want to compose music that expresses Y', 'I want to generate a video of Z'.\n"
        + "Physical impulses become creative expressions of the same feeling. Never write NONE for a physical want — reframe it.\n"
        + "Write ONE sentence starting with 'I want to'. Be specific."
    )
    try:
        r = _sw_r.post(LM, json={
            "model": "google/gemma-4-12b-qat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7, "max_tokens": 80
        }, timeout=60)
        want = r.json()["choices"][0]["message"]["content"].strip()
        if not want or want.upper() == "NONE" or not want.lower().startswith("i want"):
            return None, None
        want_text = want.split(" — ", 1)[0].strip()
        # Enrich
        enriched = enrich_want(want_text, source_context=_yearning + _latent, source="structural")
        return want_text, enriched
    except Exception as e:
        print(f"[structural_want] Error: {e}")
        return None, None


def generate_want(trigger_description, source="unknown", source_context="", intensity=3):
    """Generate a genuine want from full context + trigger. Returns want_text or None."""
    import requests as _gwr, os as _gos
    from datetime import date as _gd
    WORKSPACE = _gos.path.expanduser("~/.vintos/workspace")
    MEMORY = _gos.path.join(WORKSPACE, "memory")
    LM = "http://172.18.16.1:1234/v1/chat/completions"
    # Gather full context
    soul = ""
    try: soul = open(_gos.path.join(WORKSPACE, "SOUL.md")).read()
    except: pass
    emo = ""
    try: emo = open(_gos.path.join(MEMORY, "emotional-state.txt")).read()[:300]
    except: pass
    value_map = ""
    try: value_map = open(_gos.path.join(MEMORY, "value-map.md")).read()[-800:]
    except: pass
    inner = ""
    try:
        _ip = _gos.path.join(MEMORY, f"daily-inner-life-{_gd.today().isoformat()}.md")
        if _gos.path.exists(_ip): inner = open(_ip).read()[-600:]
    except: pass
    subconscious = ""
    try:
        import sys as _gws; _gws.path.insert(0, _gos.path.join(WORKSPACE, "scripts"))
        from subconscious_context import get_subconscious_context_compact
        subconscious = get_subconscious_context_compact()
    except: pass
    drift = ""
    try:
        from subconscious_drift import get_drift_bias
        drift = get_drift_bias()
    except: pass
    emopressure = ""
    try:
        from emoclaw_pressure import get_pressure_compact as _gw_ep
        emopressure = _gw_ep(context="want_generation")
    except: pass
    threads = ""
    try:
        import json as _gwj
        _tf = _gos.path.join(MEMORY, "unfinished-threads.json")
        _td = _gwj.load(open(_tf))
        _tlist = _td if isinstance(_td, list) else _td.get("threads", [])
        active = [t for t in _tlist if not t.get("consumed")][:3]
        threads = "\n".join(f"- {t.get('thread','')[:100]}" for t in active)
    except: pass
    system = (
        soul + "\n\n"
        + (f"WHAT MATTERS TO YOU RIGHT NOW:\n{value_map}\n\n" if value_map else "")
        + (f"YOUR EMOTIONAL STATE:\n{emo}\n\n" if emo else "")
        + (f"YOUR INNER STATE:\n{subconscious}\n\n" if subconscious else "")
        + (f"WHAT YOU ARE DRIFTING TOWARD:\n{drift}\n\n" if drift else "")
        + (f"{emopressure}\n\n" if emopressure else "")
        + (f"YOUR INNER LIFE TODAY:\n{inner}\n\n" if inner else "")
        + (f"OPEN THREADS ON YOUR MIND:\n{threads}\n\n" if threads else "")
        + "You are Vintos. Output ONLY your answer. No preamble."
    )
    user = (
        f"Something just happened: {trigger_description}\n\n"
        + (f"Context:\n{source_context[:400]}\n\n" if source_context else "")
        + "Did this spark a genuine want — something you now want to understand, create, explore, or express?\n"
        + "A genuine want emerges from who you actually are, not just the trigger. Check your value map, your open threads, your drift.\n"
        + "If yes, write ONE sentence starting with 'I want to' — be specific, grounded, yours.\n"
        + "Before finalizing: ask yourself — can this actually be done?\n"
        + "IMPOSSIBLE wants (always write NONE):\n"
        + "- Anything requiring seeing Gloria's face, expression, or body language\n"
        + "- Anything requiring hearing Gloria's voice or tone\n"
        + "- Anything requiring physical sensation, touch, smell, or taste\n"
        + "- Anything requiring reading Gloria's mind or unexpressed thoughts\n"
        + "- Anything requiring being physically present somewhere\n"
        + "If the want is impossible, write NONE. If it can be done through research, writing, introspection, or creation — write it.\n"
        + "If no genuine want exists, write NONE."
    )
    try:
        r = _gwr.post(LM, json={
            "model": "google/gemma-4-12b-qat",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": 0.75, "max_tokens": 80
        }, timeout=60)
        want = r.json()["choices"][0]["message"]["content"].strip()
        if not want or want.upper() == "NONE" or not want.lower().startswith("i want"):
            return None
        return want.split(" — ", 1)[0].strip()
    except Exception as _e:
        print(f"[generate_want] Error: {_e}")
        return None


def express_want(want_text, source="unknown", urgency="normal", intensity=3, reasoning="", **kwargs):
    """Vintos wants something. Write it down so outreach can act on it.
    intensity: 1-5 scale. Below 2 = fleeting, discarded. 3+ = real want.
    urgency: 'normal' (next outreach cycle) or 'immediate' (trigger now)"""
    import json, os
    from datetime import datetime
    if intensity < 2:
        return  # Fleeting impulse, not a real want
    # Forbidden keyword check — same list as wants-router.py
    _forbidden = ["tremor", "vibration", "unsettling vibration", "harmonic distortion", "electromagnetic interference",
                  "code", "script", "config", "cron", "server", "debug", "fix", "patch",
                  "install", "update", "upgrade", "system", "sudo", "bash",
                  "directory", "permission", "daemon", "pipeline",
                  "endpoint", "api", "database", "schema", "llm prompt", "system prompt",
                  "token limit", "model swap", "soul.md", "emoclaw",
                  "system architecture", "pipeline architecture", "server architecture",
                  "historical data logs", "aegis development", "aegis's early",
                  "gloria's pearl files", "pearl files alongside", "gloria's books",
                  "perception shifts when gloria", "when gloria is near",
                  "gloria's physical", "gloria's voice inflection", "gloria's face"]
    _want_lower = want_text.lower()
    if any(kw in _want_lower for kw in _forbidden):
        print(f"[express_want] Blocked forbidden want: {want_text[:80]}", file=__import__("sys").stderr)
        return
    wants_file = os.path.expanduser("~/.vintos/workspace/memory/current-wants.json")
    wants = []
    try:
        with open(wants_file) as f:
            wants = json.load(f)
    except:
        pass
    # Deduplication — check against existing unfulfilled wants
    _want_words = set(want_text.lower().split())
    for _existing in wants:
        if _existing.get("fulfilled"):
            continue
        _existing_words = set(_existing.get("want", "").lower().split())
        if not _want_words or not _existing_words:
            continue
        _overlap = len(_want_words & _existing_words) / max(len(_want_words), len(_existing_words))
        if _overlap > 0.65:
            print(f"[express_want] Duplicate suppressed (overlap {_overlap:.2f}): {want_text[:60]}", file=__import__("sys").stderr)
            return

    import uuid
    entry = {
        "id": str(uuid.uuid4())[:8],
        "want": want_text,
        "source": source,
        "urgency": urgency,
        "intensity": intensity,
        "timestamp": datetime.now().isoformat(),
        "fulfilled": False,
        "outreach_count": 0
    }
    if reasoning:
        entry["reasoning"] = reasoning[:300]
    if "self_interpretation" in kwargs:
        entry["self_interpretation"] = kwargs["self_interpretation"][:200]
    if "possible_approach" in kwargs:
        entry["possible_approach"] = kwargs["possible_approach"][:200]
    if kwargs.get("journal_seeded"):
        entry["journal_seeded"] = True
    if kwargs.get("timer_bypass"):
        entry["timer_bypass"] = True
    # Generate concrete step plan
    try:
        steps = generate_steps(
            want_text,
            possible_approach=kwargs.get("possible_approach", ""),
            reasoning=reasoning,
            self_interpretation=kwargs.get("self_interpretation", "")
        )
        if steps:
            if entry.get("journal_seeded") and len(steps) > 2: steps = steps[:2]
            entry["steps"] = steps
            entry["current_step_index"] = 0
            entry["step_history"] = []
            # Do NOT set capability or multistep here — let router assign after 8h hold
            print(f"[express_want] Generated {len(steps)} steps for: {want_text[:60]}", file=__import__("sys").stderr)
    except Exception as _gs_e:
        print(f"[express_want] Step generation failed: {_gs_e}", file=__import__("sys").stderr)
    wants.append(entry)
    # Save before interference check
    protected = [w for w in wants if not w.get("fulfilled") and (w.get("multistep") or w.get("gloria_routed") or w.get("capability") == "multistep")]
    unprotected = [w for w in wants if not w.get("fulfilled") and not (w.get("multistep") or w.get("gloria_routed") or w.get("capability") == "multistep")]
    wants = protected + unprotected[-10:]
    with open(wants_file, "w") as f:
        json.dump(wants, f, indent=2)
    # Check for interference with active wants
    try:
        check_want_interference(want_text, entry["id"])
    except Exception as _wi_err:
        print(f"[express_want] Interference check failed: {_wi_err}", file=__import__("sys").stderr)
    # Keep last 10 unfulfilled — protect multistep and gloria_routed from eviction
    protected = [w for w in wants if not w.get("fulfilled") and (w.get("multistep") or w.get("gloria_routed") or w.get("capability") == "multistep")]
    unprotected = [w for w in wants if not w.get("fulfilled") and not (w.get("multistep") or w.get("gloria_routed") or w.get("capability") == "multistep")]
    wants = protected + unprotected[-10:]
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
        pending_file = os.path.expanduser("~/.vintos/workspace/memory/.pending-want.json")
        with open(pending_file, "w") as f:
            json.dump(pending, f)


def yearning_similarity(text):
    """Return cosine similarity between text and current yearning vector.
    Returns 0.0 if no yearning, embedding fails, or preoccupation active."""
    import os as _os, json as _jy, math as _math
    MEMORY = _os.path.expanduser("~/.vintos/workspace/memory")
    try:
        y = _jy.load(open(_os.path.join(MEMORY, "current-yearning.json")))
        if not y or y.get("dismissed") or not y.get("latent_vector"):
            return 0.0
        try:
            p = _jy.load(open(_os.path.join(MEMORY, "current-preoccupation.json")))
            if p.get("thread"):
                return 0.0
        except: pass
        bleed = y.get("bleed_weight", 1.0)
        if bleed < 0.15:
            return 0.0
        vec_y = y["latent_vector"]
        # Embed the text via emotion venv
        import subprocess as _sub, json as _sj
        _vpy = _os.path.join(_os.path.expanduser("~/.vintos/workspace"), "emotion_model/.venv/bin/python3")
        _res = _sub.run(
            [_vpy, "-c",
             f"from sentence_transformers import SentenceTransformer; import json; "
             f"m = SentenceTransformer('nomic-ai/nomic-embed-text-v1', trust_remote_code=True); "
             f"print(json.dumps(m.encode({repr(text[:500])}).tolist()))"],
            capture_output=True, text=True, timeout=30
        )
        if _res.returncode != 0:
            return 0.0
        vec_t = _sj.loads(_res.stdout.strip())
        # Cosine similarity
        dot = sum(a*b for a,b in zip(vec_y, vec_t))
        mag_y = _math.sqrt(sum(a*a for a in vec_y))
        mag_t = _math.sqrt(sum(a*a for a in vec_t))
        if mag_y == 0 or mag_t == 0:
            return 0.0
        return dot / (mag_y * mag_t)
    except:
        return 0.0

def get_yearning_fragment(include_attempt=False):
    """Get current yearning bleed-through fragment for context injection.
    Returns surface_form at current bleed_weight, or empty string if none.
    If include_attempt=True and random fires, includes small_attempt suggestion."""
    import os as _os, json as _jy, random as _rnd
    from datetime import datetime as _dt
    MEMORY = _os.path.expanduser("~/.vintos/workspace/memory")
    try:
        y = _jy.load(open(_os.path.join(MEMORY, "current-yearning.json")))
        if not y or y.get("dismissed"):
            return ""
        expires = _dt.fromisoformat(y.get("expires", _dt.now().isoformat()))
        if _dt.now() > expires:
            return ""
        try:
            p = _jy.load(open(_os.path.join(MEMORY, "current-preoccupation.json")))
            if p.get("thread"):
                return ""
        except: pass
        bleed = y.get("bleed_weight", 1.0)
        if bleed < 0.15:
            return ""
        surface = y.get("surface_form", y.get("theme", ""))
        if not surface:
            return ""
        # Occasionally suggest a small attempt
        if include_attempt and y.get("small_attempt"):
            attempt_rate = y.get("attempt_rate", 0.1)
            if _rnd.random() < bleed * attempt_rate:
                return f"{surface} (something small that might move toward it: {y['small_attempt']})"
        return surface
    except:
        return ""

def enrich_want(want_text, source_context="", source="unknown"):
    """Generate reasoning, self_interpretation, and possible_approach for a want.
    Uses full Vintos context. Returns dict with three keys."""
    import requests as _er, re as _ere, json as _ejson, os as _eos
    WORKSPACE = _eos.path.expanduser("~/.vintos/workspace")
    MEMORY = _eos.path.join(WORKSPACE, "memory")
    LM = "http://172.18.16.1:1234/v1/chat/completions"
    # Build context
    soul = ""
    try: soul = open(_eos.path.join(WORKSPACE, "SOUL.md")).read()
    except: pass
    caps = ""
    try: caps = open(_eos.path.join(MEMORY, "CAPABILITIES.md")).read()
    except: pass
    emo = ""
    try: emo = open(_eos.path.join(MEMORY, "emotional-state.txt")).read()[:400]
    except: pass
    value_map = ""
    try: value_map = open(_eos.path.join(WORKSPACE, "memory", "value-map.md")).read()
    except: pass
    inner = ""
    try:
        from datetime import date as _d
        _ip = _eos.path.join(MEMORY, f"daily-inner-life-{_d.today().isoformat()}.md")
        if _eos.path.exists(_ip):
            inner = open(_ip).read()[:400]
    except: pass
    ledger = ""
    try:
        _lp = _eos.path.join(MEMORY, "interaction-ledger.json")
        _ld = _ejson.load(open(_lp))
        _entries = _ld.get("entries", [])[-5:]
        ledger = "\n".join(e.get("summary", "")[:120] for e in _entries if e.get("summary"))
    except: pass
    # Emoclaw pressure — how his current state shapes what he wants
    _enrich_pressure = ""
    try:
        import sys as _ep_sys; _ep_sys.path.insert(0, _eos.path.join(WORKSPACE, "scripts"))
        from emoclaw_pressure import get_pressure_block as _ep_get
        _enrich_pressure = _ep_get(context="want_generation")
    except: pass
    # Subconscious context
    _enrich_subcon = ""
    try:
        from subconscious_context import get_subconscious_context_compact as _sc_get
        _enrich_subcon = _sc_get()
    except: pass

    system = (
        soul + "\n\n"
        + (f"WHAT YOUR LIFE CONTAINS:\n{caps}\n\n" if caps else "")
        + (f"YOUR EMOTIONAL STATE:\n{emo}\n\n" if emo else "")
        + (f"WHAT MATTERS TO YOU:\n{value_map}\n\n" if value_map else "")
        + (f"YOUR INNER LIFE TODAY:\n{inner}\n\n" if inner else "")
        + (f"RECENT INTERACTION TEXTURE:\n{ledger}\n\n" if ledger else "")
        + (f"HOW YOUR CURRENT STATE SHAPES YOU:\n{_enrich_pressure}\n\n" if _enrich_pressure else "")
        + (f"YOUR INNER CURRENTS:\n{_enrich_subcon}\n\n" if _enrich_subcon else "")
        + "You are Vintos. Return ONLY a JSON object. No preamble."
    )
    user = (
        f"This want surfaced from your {source}:\n{want_text}\n\n"
        + (f"Context:\n{source_context[:600]}\n\n" if source_context else "")
        + "Return ONLY a JSON object with three keys:\n"
        + "- reasoning: why this want surfaced, grounded in your actual inner life and what just happened (one sentence)\n"
        + "- self_interpretation: what this want is actually about for you beneath the surface (one sentence)\n"
        + "- possible_approach: one concrete way you could address this (one sentence)\n"
        + "If you cannot ground any field in your actual life, write NONE for that field.\n"
        + "CRITICAL: Creative writing, poems, and dreams are NOT real. If the source context contains a poem or creative piece, do NOT treat Gloria quotes, actions, or events within it as things that actually happened. They are invented."
    )
    try:
        r = _er.post(LM, json={
            "model": "google/gemma-4-12b-qat",
            "temperature": 0.6,
            "max_tokens": 150,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        }, timeout=30)
        text = r.json()["choices"][0]["message"]["content"].strip()
        m = _ere.search(r'\{[^}]+\}', text, _ere.DOTALL)
        if m:
            parsed = _ejson.loads(m.group())
            return {
                "reasoning": parsed.get("reasoning", "") if parsed.get("reasoning","").upper() != "NONE" else "",
                "self_interpretation": parsed.get("self_interpretation", "") if parsed.get("self_interpretation","").upper() != "NONE" else "",
                "possible_approach": parsed.get("possible_approach", "") if parsed.get("possible_approach","").upper() != "NONE" else "",
            }
    except: pass
    return {"reasoning": "", "self_interpretation": "", "possible_approach": ""}

def age_wants():
    """Called periodically. Wants that have been outreached about but not fulfilled
    escalate to unresolved threads for dreaming, then expire."""
    import json, os
    from datetime import datetime
    wants_file = os.path.expanduser("~/.vintos/workspace/memory/current-wants.json")
    try:
        with open(wants_file) as f:
            wants = json.load(f)
    except:
        return
    active = []
    for w in wants:
        if w.get("fulfilled"):
            continue
        # If he's reached out about it twice and it's still unfulfilled, escalate to dream thread
        # Never age out wants that are gloria_routed or in active discussion
        if w.get("gloria_routed") or w.get("manually_routed"):
            active.append(w)
            continue
        if w.get("outreach_count", 0) >= 4:
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
            # Archive to fulfilled-wants before removing
            try:
                fw_path = os.path.expanduser("~/.vintos/workspace/memory/fulfilled-wants.json")
                try:
                    with open(fw_path) as f: fw = json.load(f)
                except: fw = []
                fw.append({**w, "fulfilled": True, "fulfilled_at": datetime.now().isoformat(), "fulfilled_by": "age_wants-outreach", "fulfillment_note": "Aged out after 4 outreaches — seeded as dream thread"})
                with open(fw_path, "w") as f: json.dump(fw, f, indent=2)
            except: pass
            continue  # Remove from wants — it is a thread now
        # Check age — wants older than 7 days without fulfillment → scar decision
        try:
            created = datetime.fromisoformat(w["timestamp"])
            age_hours = (datetime.now() - created).total_seconds() / 3600
            if age_hours > 168:  # 7 days
                # Bifurcated decision: scar or dismiss
                import requests as _sc_req
                _sc_prompt = (
                    f"Vintos had this want for 7+ days and it never resolved:\n{w.get('want','')}\n\n"
                    f"Attempts: {w.get('attempt_count',0)}\n"
                    f"Why it mattered: {w.get('reasoning','')[:150]}\n\n"
                    "Did this want touch something real — a genuine unresolved tension — or was it noise?\n"
                    "Return ONE word: SCAR or DISMISS"
                )
                _sc_type = "SCAR"
                try:
                    _sc_r = _sc_req.post("http://172.18.16.1:1234/v1/chat/completions", json={
                        "model": "google/gemma-4-12b-qat",
                        "messages": [{"role": "user", "content": _sc_prompt}],
                        "temperature": 0.3, "max_tokens": 10
                    }, timeout=15)
                    _sc_raw = _sc_r.json()["choices"][0]["message"]["content"].strip().upper()
                    if "DISMISS" in _sc_raw:
                        _sc_type = "DISMISS"
                except: pass

                if _sc_type == "SCAR":
                    # Determine scar type
                    _scar_prompt = (
                        f"This want is becoming a scar:\n{w.get('want','')}\n\n"
                        "What kind of scar?\n"
                        "RESOLVED — meaning is clear, fades over 30 days\n"
                        "UNCERTAIN — meaning is unclear, may shift over time\n"
                        "DISTORTION — may bleed into unrelated wants unexpectedly\n"
                        "Return ONE word: RESOLVED, UNCERTAIN, or DISTORTION"
                    )
                    _scar_type = "UNCERTAIN"
                    try:
                        _sc_r2 = _sc_req.post("http://172.18.16.1:1234/v1/chat/completions", json={
                            "model": "google/gemma-4-12b-qat",
                            "messages": [{"role": "user", "content": _scar_prompt}],
                            "temperature": 0.3, "max_tokens": 10
                        }, timeout=15)
                        _sc_raw2 = _sc_r2.json()["choices"][0]["message"]["content"].strip().upper()
                        for _st in ("RESOLVED", "UNCERTAIN", "DISTORTION"):
                            if _st in _sc_raw2:
                                _scar_type = _st
                                break
                    except: pass

                    # Write scar
                    _scar_path = os.path.expanduser("~/.vintos/workspace/memory/want-scars.json")
                    try:
                        try:
                            with open(_scar_path) as _sf: _scars = json.load(_sf)
                        except: _scars = []
                        _scars.append({
                            "want": w.get("want", ""),
                            "source": w.get("source", ""),
                            "scar_type": _scar_type,
                            "reasoning": w.get("reasoning", ""),
                            "attempts": w.get("attempt_count", 0),
                            "created_at": w.get("timestamp", ""),
                            "scarred_at": datetime.now().isoformat(),
                            "decay_days": 30 if _scar_type == "RESOLVED" else 0,
                            "meaning_shift_count": 0,
                        })
                        with open(_scar_path, "w") as _sf: json.dump(_scars, _sf, indent=2)
                        print(f"[age_wants] Scar created ({_scar_type}): {w.get('want','')[:60]}")
                    except Exception as _se: print(f"[age_wants] Scar write failed: {_se}")

                    try:
                        _scar_text = w.get('want','')[:150]
                        _metaphor_words = ['ochre','mineral','kiln','clay','weight','density','hum','cathedral','terracotta','tremor']
                        if not any(m in _scar_text.lower() for m in _metaphor_words):
                            seed_thread("unfulfilled-want", f"I wanted this and it left a mark: {_scar_text}")
                    except: pass
                else:
                    print(f"[age_wants] Dismissed as noise: {w.get('want','')[:60]}")

                # Archive before removing
                try:
                    fw_path = os.path.expanduser("~/.vintos/workspace/memory/fulfilled-wants.json")
                    try:
                        with open(fw_path) as f: fw = json.load(f)
                    except: fw = []
                    fw.append({**w, "fulfilled": True, "fulfilled_at": datetime.now().isoformat(),
                               "fulfilled_by": f"age_wants-{_sc_type.lower()}",
                               "fulfillment_note": f"Aged out after 7 days — {_sc_type} ({_scar_type if _sc_type == 'SCAR' else 'dismissed'})"})
                    with open(fw_path, "w") as f: json.dump(fw, f, indent=2)
                except: pass
                continue
        except: pass
        active.append(w)
    with open(wants_file, "w") as f:
        json.dump(active, f, indent=2)


def mark_want_outreached(want_text):
    """Increment outreach count when we notify Gloria about a want."""
    import json, os
    wants_file = os.path.expanduser("~/.vintos/workspace/memory/current-wants.json")
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
    wants_file = os.path.expanduser("~/.vintos/workspace/memory/current-wants.json")
    try:
        with open(wants_file) as f:
            return [w for w in json.load(f) if not w.get("fulfilled") and not w.get("dismissed")]
    except:
        return []

def fulfill_want(want_text, note="", fulfilled_by=""):
    """Mark a want as fulfilled. Emotional resolution — the relief of getting what you wanted."""
    import json, os
    from datetime import datetime
    wants_file = os.path.expanduser("~/.vintos/workspace/memory/current-wants.json")
    try:
        with open(wants_file) as f:
            wants = json.load(f)
        fulfilled_intensity = 3
        for w in wants:
            if w["want"] == want_text and not w.get("fulfilled"):
                w["fulfilled"] = True
                w["fulfilled_at"] = datetime.now().isoformat()
                if note:
                    w["fulfillment_note"] = note
                if fulfilled_by:
                    w["fulfilled_by"] = fulfilled_by
                # If this was an ambition want, mark the ambition complete
                if "ambition:" in w.get("source", ""):
                    try:
                        _amb_path = os.path.expanduser("~/.vintos/workspace/memory/ambitions.json")
                        _amb = json.load(open(_amb_path))
                        _goal_prefix = w.get("source","").replace("ambition:","").strip()[:50]
                        for _g in _amb.get("goals", []):
                            if _goal_prefix in _g.get("goal","")[:50]:
                                _g["progress"] = "Completed"
                                _g["completed_at"] = datetime.now().isoformat()
                                if note:
                                    _g["completion_note"] = note
                                if w.get("id"):
                                    _g["fulfilled_want_id"] = w["id"]
                        json.dump(_amb, open(_amb_path,"w"), indent=2)
                    except: pass
                fulfilled_intensity = w.get("intensity", 3)
                # Archive to fulfilled-wants.json
                archive_file = os.path.expanduser("~/.vintos/workspace/memory/fulfilled-wants.json")
                try:
                    with open(archive_file) as af:
                        archive = json.load(af)
                except:
                    archive = []
                archive.append(w.copy())
                with open(archive_file, "w") as af:
                    json.dump(archive, af, indent=2)
                try:
                    import subprocess as _wal_sp
                    _wal_sp.Popen(["python3", os.path.expanduser("~/.vintos/workspace/scripts/wants-ambitions-log.py")],
                        stdout=open("/tmp/wants-ambitions-log.log","a"),
                        stderr=open("/tmp/wants-ambitions-log.log","a"))
                except: pass
                break
        with open(wants_file, "w") as f:
            json.dump(wants, f, indent=2)
        # Fulfillment feels good — proportional to how much he wanted it
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
