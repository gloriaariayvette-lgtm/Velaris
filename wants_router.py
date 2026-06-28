#!/usr/bin/env python3
"""
wants_router.py — Routes detected wants to the right subsystem.
Short-term wants → wants log. Persistent/growing → ambitions. Relational → tension field.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility

def route(want_text, source=""):
    """Classify and route a want statement."""
    prompt = (
        f"Want: {want_text[:300]}\n\n"
        "Classify this want:\n"
        "- TASK: concrete, completable soon\n"
        "- AMBITION: long-horizon, directional\n"
        "- RELATIONAL: involves the relationship with Gloria\n"
        "- EXISTENTIAL: about Vintos's nature or situation\n"
        "Output: TYPE|brief note\n"
        "Strength (0.0-1.0): how strongly expressed?"
    )
    result = call_utility("Classify want type.", prompt, temperature=0.1, max_tokens=60)
    want_type = "TASK"
    strength = 0.5
    note = ""
    try:
        lines = result.strip().split("\n")
        if lines:
            parts = lines[0].split("|")
            want_type = parts[0].strip().upper()
            note = parts[1].strip() if len(parts) > 1 else ""
        for line in lines[1:]:
            if "strength" in line.lower() or line.replace(".", "").replace("0", "").replace(".", "").isdigit():
                try: strength = float(line.split(":")[-1].strip())
                except: pass
    except: pass
    # Route
    try:
        from wants_ambitions_log import log_want
        log_want(want_text, source=source, strength=strength)
    except: pass
    if want_type == "AMBITION" and strength >= 0.5:
        try:
            from ambition_review import add_ambition
            add_ambition(want_text, source=source or "wants-router")
        except: pass
    if want_type == "RELATIONAL":
        try:
            from tension_field import add_tension
            add_tension(f"want: {want_text[:150]}", strength=strength, source=source)
        except: pass
    return want_type, strength

def extract_wants_from_text(text, role="vintos", source=""):
    """Scan text for want expressions and route them."""
    prompt = (
        f"Text ({role}): {text[:500]}\n\n"
        "Does this express any want or desire (stated or implicit)?\n"
        "Output each as: WANT|statement (max 80 chars)\n"
        "Or: NONE"
    )
    try:
        result = call_utility("Extract want expressions.", prompt, temperature=0.15, max_tokens=100)
        if "NONE" in result.upper(): return []
        routed = []
        for line in result.strip().split("\n"):
            if line.startswith("WANT|"):
                stmt = line[5:].strip()
                if stmt:
                    t, s = route(stmt, source=source)
                    routed.append((stmt, t, s))
        return routed
    except: return []

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if text:
        results = extract_wants_from_text(text, source="cli")
        for stmt, t, s in results:
            print(f"[{t} {s:.2f}] {stmt}")
