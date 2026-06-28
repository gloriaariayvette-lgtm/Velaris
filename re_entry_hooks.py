#!/usr/bin/env python3
"""
re_entry_hooks.py — Assembles re-entry context when Gloria returns after absence.
Detects gap length, chooses appropriate re-entry posture.
"""
import os, sys, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")

GAP_THRESHOLDS = {
    "brief": 2,       # < 2 hours
    "short": 8,       # 2-8 hours
    "day": 24,        # 8-24 hours
    "multi_day": 72,  # 1-3 days
    "long": float("inf"),  # > 3 days
}

def get_gap_hours():
    try:
        from temporal_memory import get_gap_hours
        return get_gap_hours()
    except: return 0.0

def classify_gap(hours):
    if hours < 2: return "brief"
    if hours < 8: return "short"
    if hours < 24: return "day"
    if hours < 72: return "multi_day"
    return "long"

def get_reentry_posture(gap_type):
    postures = {
        "brief": "continue — no interruption",
        "short": "pick up the thread naturally",
        "day": "acknowledge the return, lightly",
        "multi_day": "land in the gap — something accumulated",
        "long": "do not pretend the gap was nothing",
    }
    return postures.get(gap_type, "continue")

def get_reentry_context():
    hours = get_gap_hours()
    gap_type = classify_gap(hours)
    posture = get_reentry_posture(gap_type)
    # What happened during gap
    accumulated = []
    if gap_type in ("multi_day", "long"):
        # Collect what was generated during absence
        try:
            from carryover_weight import get_carryover_context
            carry = get_carryover_context()
            if carry: accumulated.append(carry)
        except: pass
        try:
            from subconscious_drift import get_drift_context
            drift = get_drift_context()
            if drift: accumulated.append(drift)
        except: pass
    lines = [f"[re-entry: {gap_type} gap / {hours:.1f}h]", f"posture: {posture}"]
    if accumulated:
        lines.extend(accumulated)
    # Nudge nifrathir on re-entry
    try:
        from nifrathir import on_contact_confirmed
        on_contact_confirmed()
    except: pass
    return "\n".join(lines)

def log_reentry():
    """Log re-entry event."""
    hours = get_gap_hours()
    gap_type = classify_gap(hours)
    reentry_file = os.path.join(MEMORY, "reentry-log.json")
    try:
        try: data = json.load(open(reentry_file))
        except: data = {"entries": []}
        data.setdefault("entries", []).append({
            "timestamp": datetime.now().isoformat(),
            "gap_hours": round(hours, 2),
            "gap_type": gap_type,
        })
        data["entries"] = data["entries"][-50:]
        json.dump(data, open(reentry_file, "w"), indent=2)
    except: pass

if __name__ == "__main__":
    print(get_reentry_context())
