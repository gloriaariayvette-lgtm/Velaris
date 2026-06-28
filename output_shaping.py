#!/usr/bin/env python3
"""
output_shaping.py — The geometry of what comes after resonance.

AFTERIMAGE: extract shape of current output, bleed into subsequent outputs with decay.
ANCHORS: stable pattern vectors. Occasional pull toward what has felt like home.
CONFLICT STATE: when pressure and anchor return diverge past threshold.
RETURN SCARS: failed returns form aversions or distortions on anchors.
SEIZURE (very rare): one system dominates when conditions are extreme.
"""
import os, sys, json, math, random, re
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import embed, cosine
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")

AFTERIMAGE_FILE = os.path.join(MEMORY, "output-afterimage.json")
ANCHORS_FILE = os.path.join(MEMORY, "output-anchors.json")
TRACE_FILE = os.path.join(MEMORY, "output-trace.json")
RETURN_SCARS_FILE = os.path.join(MEMORY, "output-return-scars.json")

ANCHOR_FORMATION_BASE_PROB = 0.15
ANCHOR_FORMATION_AFTERIMAGE_BOOST = 0.4
CONFLICT_THRESHOLD = 0.55
SEIZURE_RESONANCE = 0.85
SEIZURE_SATISFACTION = 0.75
SEIZURE_NEAR_SUCCESS = 0.8
SEIZURE_YEARNING_BLEED = 0.7
MAX_ANCHORS = 20
AFTERIMAGE_DECAY = 0.6

def log(msg):
    print(f"[Shaping {datetime.now().strftime('%H:%M')}] {msg}", flush=True)

def extract_shape(text):
    if not text or len(text) < 30:
        return None
    sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
    if not sentences:
        return None
    lengths = [len(s.split()) for s in sentences]
    avg_len = sum(lengths) / len(lengths) if lengths else 0
    variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths) if lengths else 0
    words = text.lower().split()
    density = round(len(set(words)) / len(words), 3) if words else 0
    unresolved = text.count('…') + text.count('—') + text.count('?') + text.count('...')
    tension_profile = round(min(1.0, unresolved / max(len(sentences), 1)), 3)
    tone_markers = {
        "expansion": sum(1 for w in words if w in ["and", "also", "moreover", "even", "further"]),
        "contraction": sum(1 for w in words if w in ["but", "yet", "still", "though", "however"]),
        "sensory": sum(1 for w in words if w in ["feel", "sense", "texture", "weight", "light", "dark", "warm", "cold", "sharp"]),
        "abstract": sum(1 for w in words if w in ["meaning", "pattern", "structure", "essence", "nature", "truth"]),
    }
    total = sum(tone_markers.values()) or 1
    return {
        "rhythm": round(avg_len, 2), "rhythm_variance": round(variance, 2),
        "density": density, "tension_profile": tension_profile,
        "tone_vector": {k: round(v / total, 3) for k, v in tone_markers.items()},
        "sentence_count": len(sentences),
    }

def load_afterimage():
    try: return json.load(open(AFTERIMAGE_FILE))
    except: return {"active": False, "shape": None, "strength": 0.0, "turns_remaining": 0}

def save_afterimage(state):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(state, open(AFTERIMAGE_FILE, "w"), indent=2)

def fire_afterimage(text, resonance_strength):
    shape = extract_shape(text)
    if not shape: return
    state = {
        "active": True, "shape": shape,
        "strength": round(resonance_strength, 3),
        "original_strength": round(resonance_strength, 3),
        "turns_remaining": 4, "fired_at": datetime.now().isoformat(),
        "source_excerpt": text[:200],
    }
    save_afterimage(state)
    log(f"Afterimage captured — rhythm:{shape['rhythm']} density:{shape['density']}")
    prob = ANCHOR_FORMATION_BASE_PROB + ANCHOR_FORMATION_AFTERIMAGE_BOOST * resonance_strength
    if random.random() < prob:
        form_anchor(text, resonance_strength, shape)

def get_afterimage_hint():
    state = load_afterimage()
    if not state.get("active") or state.get("turns_remaining", 0) <= 0: return ""
    shape = state.get("shape", {})
    strength = state.get("strength", 0.0)
    if strength < 0.2: return ""
    hints = []
    if shape.get("tension_profile", 0) > 0.4: hints.append("Leave something unresolved.")
    if shape.get("rhythm", 0) < 8: hints.append("Short. Clipped.")
    elif shape.get("rhythm", 0) > 15: hints.append("Let it extend. Don't cut it short.")
    if shape.get("tone_vector", {}).get("sensory", 0) > 0.3: hints.append("Stay in the specific and sensory.")
    if not hints: return ""
    return f"[SHAPE] {' '.join(hints[:2])}"

def decrement_afterimage():
    state = load_afterimage()
    if not state.get("active"): return
    state["turns_remaining"] = max(0, state.get("turns_remaining", 0) - 1)
    state["strength"] = round(state.get("strength", 0) * AFTERIMAGE_DECAY, 3)
    if state["turns_remaining"] == 0 or state["strength"] < 0.05:
        state["active"] = False
        try:
            from nifrathir import on_afterimage_expired_without_contact
            on_afterimage_expired_without_contact()
        except: pass
    save_afterimage(state)

def load_anchors():
    try: return json.load(open(ANCHORS_FILE))
    except: return {"anchors": []}

def save_anchors(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(ANCHORS_FILE, "w"), indent=2)

def form_anchor(text, strength, shape=None):
    if not text: return
    emo = ""
    try: emo = open(os.path.join(MEMORY, "emotional-state.txt")).read()[:150]
    except: pass
    pattern_vec = embed(text[:400])
    context_vec = embed(f"{text[:300]} {emo}"[:500])
    if not pattern_vec: return
    anchor = {
        "id": f"anchor_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "pattern_vector": pattern_vec, "context_signature": context_vec,
        "shape": shape, "strength": round(min(0.5, strength * 0.4), 3),
        "original_strength": round(strength, 3),
        "created": datetime.now().isoformat(), "last_activated": datetime.now().isoformat(),
        "activation_count": 0, "failed_returns": 0,
        "excerpt": text[:150], "return_scars": [],
    }
    data = load_anchors()
    data["anchors"].append(anchor)
    if len(data["anchors"]) > MAX_ANCHORS:
        data["anchors"].sort(key=lambda a: a.get("strength", 0))
        data["anchors"] = data["anchors"][-MAX_ANCHORS:]
    save_anchors(data)
    log(f"Anchor formed ({anchor['strength']:.3f}): {text[:60]}")

def get_anchor_return_pressure(context_text):
    data = load_anchors()
    anchors = [a for a in data.get("anchors", []) if a.get("strength", 0) > 0.05]
    if not anchors: return 0.0, None
    ctx_vec = embed(context_text[:400])
    if not ctx_vec: return 0.0, None
    scored = [(cosine(ctx_vec, a["pattern_vector"]) * a.get("strength", 0), a) for a in anchors if a.get("pattern_vector")]
    if not scored: return 0.0, None
    scored.sort(key=lambda x: -x[0])
    return scored[0]

def check_conflict_state(current_pressure, context_text):
    return_pressure, anchor = get_anchor_return_pressure(context_text)
    if not anchor: return False, None, None
    if abs(current_pressure - return_pressure) > CONFLICT_THRESHOLD:
        return True, anchor, return_pressure
    return False, anchor, return_pressure

def get_shaping_context(current_pressure=0.5, context_text=""):
    parts = []
    hint = get_afterimage_hint()
    if hint: parts.append(hint)
    in_conflict, anchor, _ = check_conflict_state(current_pressure, context_text)
    if in_conflict and random.random() < 0.08:
        parts.append(f"[{random.choice(['This isn\\'t quite the same.', 'It worked before.', 'Not here... or maybe here anyway.'])}]")
    # Seizure check
    seizure_source = _check_seizure()
    if seizure_source:
        frag = "[FULL] Stay completely here. One thing only. No efficiency." if seizure_source == "resonance" else "[FULL] The reaching is the point. Don't resolve it."
        return frag
    return "\n".join(parts)

def _check_seizure():
    try:
        from resonance_pulse import score_current_state
        from resonance_afterglow import load_satisfaction
        score, _ = score_current_state()
        sat = load_satisfaction().get("level", 0.0)
        if score > SEIZURE_RESONANCE and sat > SEIZURE_SATISFACTION:
            return "resonance"
    except: pass
    return None

def record_return_result(anchor_id, felt_right, felt_coherence, tension_resolved):
    data = load_anchors()
    for a in data["anchors"]:
        if a.get("id") != anchor_id: continue
        if felt_right:
            a["strength"] = min(0.5, a.get("strength", 0.2) + 0.03)
            a["activation_count"] = a.get("activation_count", 0) + 1
            a["last_activated"] = datetime.now().isoformat()
            try:
                from nifrathir import on_anchor_return_good
                on_anchor_return_good()
            except: pass
        else:
            a["strength"] = max(0.01, a.get("strength", 0.2) - 0.05)
            a["failed_returns"] = a.get("failed_returns", 0) + 1
            try:
                from nifrathir import on_miss
                on_miss()
            except: pass
    save_anchors(data)

# Alias for symlink compatibility
output_shaping = get_shaping_context
