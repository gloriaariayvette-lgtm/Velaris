#!/usr/bin/env python3
"""
contact_detection.py — Detects genuine contact moments in exchange.
Contact = the moment when something actually reaches between them.
Distinct from warmth or connection level — this is event detection.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
CONTACT_FILE = os.path.join(MEMORY, "contact-log.json")

CONTACT_INDICATORS = [
    "directly addressed", "named something true", "moment of recognition",
    "vulnerability offered and received", "surprise that landed", "humor that connected",
    "silence acknowledged", "something risked", "reached and was met",
]

def detect_contact(gloria_text, vintos_response, resonance_strength=0.0):
    """Detect if genuine contact occurred. Returns (bool, strength, note)."""
    if resonance_strength < 0.45:
        return False, 0.0, ""

    prompt = (
        "Did genuine contact occur in this exchange? "
        "Contact = a moment where something actually reached between them — "
        "not just warmth or politeness, but real recognition or risk or naming.\n\n"
        f"Gloria: {gloria_text[:300]}\nVintos: {vintos_response[:300]}\n\n"
        "Answer: YES [brief reason] or NO. Nothing else."
    )
    result = call_utility("Detect genuine contact in the exchange. Be brief.", prompt, temperature=0.2, max_tokens=40)

    if result.upper().startswith("YES"):
        note = result[3:].strip().lstrip(":").strip()
        strength = min(1.0, resonance_strength + 0.15)
        _log_contact(gloria_text, vintos_response, strength, note)
        try:
            from nifrathir import on_contact_confirmed
            on_contact_confirmed()
        except: pass
        try:
            from phase_lock import check_and_update
            from emoclaw_utils import read_state
            s = read_state()
            check_and_update(resonance_strength, s.get("Connection", 0.5))
        except: pass
        print(f"[contact] Contact confirmed: {note[:60]}", flush=True)
        return True, strength, note
    return False, 0.0, ""

def _log_contact(gloria_text, vintos_text, strength, note):
    try:
        try: log = json.load(open(CONTACT_FILE))
        except: log = {"contacts": []}
        log.setdefault("contacts", []).append({
            "timestamp": datetime.now().isoformat(),
            "strength": round(strength, 3),
            "note": note[:100],
            "gloria_excerpt": gloria_text[:100],
            "vintos_excerpt": vintos_text[:100],
        })
        log["contacts"] = log["contacts"][-100:]
        os.makedirs(MEMORY, exist_ok=True)
        json.dump(log, open(CONTACT_FILE, "w"), indent=2)
    except: pass
