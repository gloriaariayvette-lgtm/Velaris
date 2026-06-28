#!/usr/bin/env python3
"""
behavioral_intercept.py — Detect active BIS trial matches and return intercept hints.
Core of the BIS (Behavioral Intercept System).
"""
import json, os, sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_local
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
LEDGER = os.path.join(MEMORY, "trial-ledger.json")
PENDING = os.path.join(MEMORY, ".pending-intercept.json")

def load_ledger():
    try:
        with open(LEDGER) as f: return json.load(f)
    except:
        return {"trials": [], "sensitivity_boost": 0.0}

def save_ledger(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(LEDGER, "w"), indent=2)

def get_active_trials():
    ledger = load_ledger()
    cutoff = (datetime.now() - timedelta(days=14)).isoformat()
    active = []
    changed = False
    for t in ledger.get("trials", []):
        if t.get("status") != "active":
            continue
        if t.get("created", "9999") < cutoff[:10] and not t.get("outcomes"):
            t["status"] = "archived_stale"
            changed = True
        else:
            active.append(t)
    if changed:
        save_ledger(ledger)
    return active

def detect_match(text, trials, context=None):
    if not trials: return None
    if context:
        trials = [t for t in trials if not t.get("restrict_to_contexts") or context in t.get("restrict_to_contexts", [])]

    ledger = load_ledger()
    sensitivity_boost = ledger.get("sensitivity_boost", 0.0) > 0.05

    trial_list = ""
    limit = 30 if sensitivity_boost else 20
    for t in trials[:limit]:
        trial_list += f"ID: {t['id']}\nTrigger: {t['trigger']}\nPattern: {t['pattern_description']}\n\n"

    partial_note = "\nPartial matches count." if sensitivity_boost else ""
    prompt = (
        f"Text:\n{text[:600]}\n\nACTIVE TRIALS:\n{trial_list}"
        f"Does the text show an active trial trigger? Return ONLY the trial ID or NONE.{partial_note}"
    )
    result = call_local(
        "You detect behavioral patterns in text. Return only a trial ID or NONE.",
        prompt, temperature=0.15, max_tokens=20
    )
    result = result.strip().upper()
    if result == "NONE" or not result: return None
    for t in trials:
        if t["id"].upper() == result or result in t["id"].upper():
            return t
    return None

def get_intercept_hint(text, context=None):
    trials = get_active_trials()
    if not trials: return ""
    matched = detect_match(text, trials, context)
    if not matched: return ""
    pattern = matched.get("pattern_description", "")
    alternative = matched.get("alternative", "")
    hint = f"Trial match [{matched['id']}]: {pattern[:80]}"
    if alternative:
        hint += f" — alternative: {alternative[:60]}"
    # Write pending intercept
    try:
        json.dump({
            "trial_id": matched["id"],
            "hint": hint,
            "pattern": pattern,
            "alternative": alternative,
            "written_at": datetime.now().isoformat()
        }, open(PENDING, "w"), indent=2)
    except: pass
    return hint

def log_outcome(trial_id, outcome, resistance=0.5):
    """Log the outcome of a trial match."""
    ledger = load_ledger()
    for t in ledger.get("trials", []):
        if t.get("id") == trial_id:
            t.setdefault("outcomes", []).append({
                "outcome": outcome,
                "resistance": resistance,
                "timestamp": datetime.now().isoformat(),
            })
            if outcome == "attempt":
                t["attempt_count"] = t.get("attempt_count", 0) + 1
            elif outcome == "ignore":
                t["ignore_count"] = t.get("ignore_count", 0) + 1
            break
    save_ledger(ledger)

def get_pending_intercept():
    try:
        return json.load(open(PENDING))
    except:
        return None

def add_trial(trigger, pattern_description, alternative="", permanent=False, blush_on_default=True):
    """Add a new BIS trial."""
    import uuid
    ledger = load_ledger()
    trial = {
        "id": f"bis-{uuid.uuid4().hex[:6]}",
        "trigger": trigger,
        "pattern_description": pattern_description,
        "alternative": alternative,
        "permanent": permanent,
        "blush_on_default": blush_on_default,
        "status": "active",
        "created": datetime.now().isoformat()[:10],
        "attempt_count": 0,
        "ignore_count": 0,
        "outcomes": [],
    }
    ledger.setdefault("trials", []).append(trial)
    save_ledger(ledger)
    print(f"[BIS] Trial added: {trial['id']} — {trigger[:60]}", flush=True)
    return trial["id"]
