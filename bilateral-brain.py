#!/usr/bin/env python3
"""
bilateral-brain.py — Vintos generation pipeline.

A1 (analytical) + B1 (emotional/intuitive) run in parallel.
BIS 1.5 intercepts on the raw outputs.
Absorb merges A1+B1 into a unified draft.
BIS 2.5 intercepts on the absorbed draft.
Synthesis generates the final response.
BIS Final checks for active trial matches.
Deviation check scores the output against Core.

Usage:
  python3 bilateral-brain.py <system_prompt_file> <user_msg_file>
  Returns final response to stdout.
  Writes BIS intercept hints to /tmp/bis-intercept.txt if active.
"""

import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")

from model_utils import call, call_utility
from model_config import VINTOS_MODEL, UTILITY_MODEL

def log(msg):
    print(f"[bilateral {datetime.now().strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)

def get_subcon():
    try:
        from subconscious_context import get_subconscious_context_compact
        return get_subconscious_context_compact()
    except:
        return ""

def get_emo_pressure():
    try:
        from emoclaw_pressure import get_pressure_block
        return get_pressure_block()
    except:
        return ""

def get_ghost_lean(a1_text, b1_text):
    try:
        from ghost_lean import get_lean_hint
        return get_lean_hint(a1_text, b1_text)
    except:
        return ""

def run_bis(text, pass_name="1.5", context=None):
    """Run BIS intercept check. Returns (intercept_hint, trial_id) or ("", None)."""
    try:
        from behavioral_intercept import get_intercept_hint, get_pending_intercept
        hint = get_intercept_hint(text, context=context)
        return hint or "", None
    except:
        return "", None

def run_deviation(text, gloria_msg=""):
    """Run deviation check. Returns result dict."""
    try:
        from deviation_check import check
        return check(text, gloria_msg)
    except:
        return {"deviation": 0.0, "alignment": 0.0, "result": "neutral"}

def build_system(base_system, subcon, emo_pressure, bis_hint="", ghost_lean=""):
    parts = [base_system.strip()]
    if subcon:
        parts.append(subcon)
    if emo_pressure:
        parts.append(emo_pressure)
    if ghost_lean:
        parts.append(ghost_lean)
    if bis_hint:
        parts.append(f"[BIS ACTIVE — behavioral intercept: {bis_hint}]")
    return "\n\n".join(parts)

def run(system_text, user_text):
    subcon = get_subcon()
    emo = get_emo_pressure()
    log("subcon and emo loaded")

    # A1 — analytical hemisphere: structured, reasoned, grounded
    a1_system = build_system(
        system_text + "\n\n[A1 — ANALYTICAL HEMISPHERE: Be precise, grounded, specific. Follow the argument. No decoration.]",
        subcon, emo
    )
    log("A1 generating...")
    a1_text = call(a1_system, user_text, temperature=0.5, max_tokens=600)
    log(f"A1 done ({len(a1_text)} chars)")

    # B1 — intuitive hemisphere: emotional, associative, alive
    b1_system = build_system(
        system_text + "\n\n[B1 — INTUITIVE HEMISPHERE: Follow feeling and association. Don't explain — reach. Let the unexpected in.]",
        subcon, emo
    )
    log("B1 generating...")
    b1_text = call(b1_system, user_text, temperature=1.0, max_tokens=600)
    log(f"B1 done ({len(b1_text)} chars)")

    ghost_lean = get_ghost_lean(a1_text, b1_text)

    # BIS 1.5 — intercept on raw outputs
    combined_raw = f"{a1_text}\n\n{b1_text}"
    bis_1_5_hint, _ = run_bis(combined_raw, pass_name="1.5", context="generation")
    if bis_1_5_hint:
        log(f"BIS 1.5 fired: {bis_1_5_hint[:60]}")

    # Absorb — merge A1 + B1
    absorb_system = build_system(
        system_text + "\n\n[ABSORB: You have two drafts below. Do not average them. Find the alive thing in each and carry it forward into a unified internal draft. Keep what has real weight. Drop what is performance.]",
        subcon, emo, bis_hint=bis_1_5_hint, ghost_lean=ghost_lean
    )
    absorb_prompt = f"DRAFT A (analytical):\n{a1_text[:1200]}\n\nDRAFT B (intuitive):\n{b1_text[:1200]}\n\nUser said: {user_text[:400]}"
    log("Absorbing...")
    absorbed = call(absorb_system, absorb_prompt, temperature=0.7, max_tokens=600)
    log(f"Absorbed ({len(absorbed)} chars)")

    # BIS 2.5 — intercept on absorbed draft
    bis_2_5_hint, _ = run_bis(absorbed, pass_name="2.5", context="generation")
    if bis_2_5_hint:
        log(f"BIS 2.5 fired: {bis_2_5_hint[:60]}")

    # Synthesis — final generation
    synth_system = build_system(
        system_text,
        subcon, emo, bis_hint=bis_2_5_hint, ghost_lean=ghost_lean
    )
    synth_prompt = f"[Internal draft — do not show, do not reference, just respond from it:]\n{absorbed[:1600]}\n\nRespond now to: {user_text[:600]}"
    log("Synthesis generating...")
    final = call(synth_system, synth_prompt, temperature=0.82, max_tokens=4096)
    log(f"Synthesis done ({len(final)} chars)")

    # BIS Final — last intercept pass on final output
    bis_final_hint, trial_id = run_bis(final, pass_name="final", context="output")
    if bis_final_hint:
        log(f"BIS Final fired: {bis_final_hint[:60]}")
        open("/tmp/bis-intercept.txt", "w").write(bis_final_hint)
    else:
        try:
            os.remove("/tmp/bis-intercept.txt")
        except:
            pass

    # Deviation check
    dev_result = run_deviation(final, gloria_msg=user_text)
    log(f"Deviation check: {dev_result.get('result','?')} (dev={dev_result.get('deviation',0):.2f} aln={dev_result.get('alignment',0):.2f})")

    # Decrement afterimage
    try:
        from output_shaping import decrement_afterimage
        decrement_afterimage()
    except:
        pass

    # Output coherence pressure — append voice if deviation fired
    if dev_result.get("voice"):
        final = final + f"\n\n{dev_result['voice']}"

    return final

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: bilateral-brain.py <system_file> <user_file>", file=sys.stderr)
        sys.exit(1)
    system_text = open(sys.argv[1]).read()
    user_text = open(sys.argv[2]).read()
    output = run(system_text, user_text)
    print(output)
