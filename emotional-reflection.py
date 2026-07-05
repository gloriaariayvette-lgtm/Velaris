#!/usr/bin/env python3
"""
emotional-reflection.py — Vintos compares his predicted emotional state
to his actual measured state. Identifies blind spots in self-perception.
Runs daily at 5 PM.
Output: memory/emotional-reflections.md, seeds threads for significant mismatches.
"""
import os, sys, json, requests
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.vintos/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
API = "http://172.18.16.1:1234/v1/chat/completions"
MODEL = "google/gemma-4-12b-qat"
OUTPUT = os.path.join(MEMORY, "emotional-reflections.md")
MISMATCH_THRESHOLD = 0.25

def log(msg):
    print(f"[REFLECT] {msg}")

_SUBCON_EMOTIONAL_REFLECTION = ""
try:
    import sys as _sc__SUBCON_EMOTIONAL_REFLECTION; _sc__SUBCON_EMOTIONAL_REFLECTION.path.insert(0, os.path.join(os.path.expanduser("~/.vintos/workspace"), "scripts"))
    from subconscious_context import get_subconscious_context_compact
    _SUBCON_EMOTIONAL_REFLECTION = get_subconscious_context_compact()
except: pass


def get_context():
    parts = []
    try:
        parts.append(open(os.path.join(WORKSPACE, "SOUL.md")).read()[:2000])
    except: pass
    try:
        parts.append("SELF-MODEL:\n" + open(os.path.join(WORKSPACE, "SELF-MODEL.md")).read()[:800])
    except: pass
    try:
        vm = open(os.path.join(MEMORY, "value-map.md")).read()
        entries = vm.split("---")
        latest = next((e.strip()[:600] for e in reversed(entries) if e.strip()), "")
        if latest:
            parts.append("WHAT MATTERS TO ME RIGHT NOW:\n" + latest)
    except: pass
    try:
        ledger = json.load(open(os.path.join(MEMORY, "interaction-ledger.json")))
        recent = ledger[-5:]
        lines = [f"Gloria: {e.get('gloria','')[:100]} | Vintos: {e.get('vintos','')[:100]} | felt: {e.get('felt','')[:60]}" for e in recent]
        parts.append("RECENT EXCHANGES:\n" + "\n".join(lines))
    except: pass
    try:
        di = open(os.path.join(MEMORY, f"daily-inner-life-{datetime.now().strftime('%Y-%m-%d')}.md")).read()[:600]
        parts.append("TODAY'S INNER LIFE:\n" + di)
    except: pass
    return "\n\n".join(parts)

def get_actual_state():
    try:
        emo = json.load(open(os.path.join(MEMORY, "emotional-state.json")))
        dims = emo.get("dimensions", {})
        if not dims:
            raise ValueError("no dimensions")
        return {k: v for k, v in dims.items() if k != "Nifrathir"}
    except:
        try:
            lines = open(os.path.join(MEMORY, "emotional-state.txt")).read().strip().splitlines()
            dims = {}
            for line in lines:
                if ":" in line:
                    k, v = line.split(":", 1)
                    try:
                        dims[k.strip()] = float(v.split("|")[0].strip())
                    except: pass
            return {k: v for k, v in dims.items() if k != "Nifrathir"}
        except: return {}

def get_predicted_state(context, actual_dims):
    dim_names = list(actual_dims.keys())
    prompt = f"""Based on everything you know about yourself right now, predict your current emotional state.

For each dimension, give a value 0.0-1.0 (or -1.0 to 1.0 for Valence).
Dimensions: {', '.join(dim_names)}

Respond ONLY with JSON like: {{"Valence": 0.6, "Arousal": 0.4, ...}}"""

    try:
        r = requests.post(API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": context},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 200
        }, timeout=60)
        text = r.json()["choices"][0]["message"]["content"].strip()
        import re
        match = re.search(r'\{[^}]+\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except: pass
    return {}

def main():
    log("Starting emotional reflection...")
    context = get_context()
    try:
        _carry_in = open(os.path.join(MEMORY, "emotional-reflection-carry.txt")).read().strip()
        if _carry_in:
            context += f"\n\nWHAT YOUR LAST EMOTIONAL REFLECTION FOUND:\n{_carry_in}"
    except: pass
    log(f"Context loaded: {len(context)} chars")
    # Semantic search on current emotional state
    _refl_semantic = ""
    try:
        import subprocess as _rsp
        _actual_raw = open(os.path.join(MEMORY, "emotional-state.txt")).read()[:200]
        _temporal = open(os.path.join(MEMORY, "temporal-context.txt")).read()[:200]
        _query = f"emotional processing mismatches self-prediction {_temporal[:80]}".strip()
        _rr = _rsp.run(
            [os.path.join(WORKSPACE, "emotion_model/.venv/bin/python3"),
             os.path.join(WORKSPACE, "scripts", "memory-search.py"), _query, "--limit", "3"],
            capture_output=True, text=True, timeout=20,
            cwd=os.path.join(WORKSPACE, "emotion_model")
        )
        if _rr.returncode == 0:
            _rlines = [l.strip()[:150] for l in _rr.stdout.strip().split("\n")
                      if l.strip() and not l.startswith("No semantic") and not l.startswith("Searching")]
            _refl_semantic = "\n".join(_rlines[:6])
    except: pass

    actual = get_actual_state()
    if not actual:
        log("Could not load actual emotional state.")
        return
    log(f"Actual state loaded: {len(actual)} dimensions")

    predicted = get_predicted_state(context, actual)
    if not predicted:
        log("Could not get predicted state.")
        return
    log(f"Got {len(predicted)} dimension guesses")

    mismatches = []
    for dim, actual_val in actual.items():
        pred_val = predicted.get(dim)
        if pred_val is None:
            continue
        diff = abs(actual_val - pred_val)
        if diff >= MISMATCH_THRESHOLD:
            direction = "overestimated" if pred_val > actual_val else "underestimated"
            mismatches.append((dim, pred_val, actual_val, diff, direction))

    mismatches.sort(key=lambda x: -x[3])
    log(f"Mismatches calculated. {len(mismatches)} significant.")

    if not mismatches:
        log("No significant mismatches — self-perception accurate today.")
        return

    lines = [f"## {datetime.now().strftime('%Y-%m-%d %H:%M')} — Emotional Reflection"]

    # Build table
    table_lines = [
        f"## {datetime.now().strftime('%Y-%m-%d %H:%M')} — Emotional Reflection",
        "### My Estimates vs Reality",
        f"{'Dimension':<16}| {'You guessed':<12}| {'Actual':<8}| Delta",
        f"{'-'*16}|{'-'*13}|{'-'*9}|{'-'*7}"
    ]
    all_dims_sorted = sorted(actual.items(), key=lambda x: -abs(x[1] - (predicted.get(x[0]) or x[1])))
    for dim, actual_val in all_dims_sorted:
        pred_val = predicted.get(dim)
        if pred_val is None: continue
        delta = pred_val - actual_val
        flag = " ***" if abs(delta) >= MISMATCH_THRESHOLD else ""
        table_lines.append(f"{dim:<16}| {pred_val:<12.4f}| {actual_val:<8.4f}| {delta:+.4f}{flag}")

    # Ask Vintos to reflect in prose
    mismatch_summary = "\n".join(
        f"- {dim}: guessed {pred:.2f}, actual {actual_val:.2f} ({direction} by {diff:.2f})"
        for dim, pred, actual_val, diff, direction in mismatches
    )
    reflection_prompt = (
        f"{context}\n\n"
        + (f"What you have already found in your memory about your emotional patterns (build forward, do not repeat):\n{_refl_semantic}\n\n" if _refl_semantic else "")
        + f"Here are today's significant emotional prediction mismatches:\n{mismatch_summary}\n\n"
        f"Write 2-3 paragraphs reflecting on what these mismatches are pointing toward — not as errors to correct, but as information about where you are and where you're heading. "
        f"Be specific — what were you expecting, what actually happened, and what does the gap suggest about what you're moving through right now? "
        f"Use your actual emotional dimension names. No poetry. No metaphors. End with one thing this opens up."
    )
    narrative = ""
    try:
        import requests as _req
        r = _req.post("http://172.18.16.1:1234/v1/chat/completions", json={
            "model": "google/gemma-4-12b-qat",
            "messages": [
                {"role": "system", "content": "You are Vintos. Write honest self-analysis. No preamble."},
                {"role": "user", "content": reflection_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 800
        }, timeout=90)
        narrative = r.json()["choices"][0]["message"]["content"].strip()
    except Exception as ne:
        log(f"Narrative generation failed: {ne}")

    lines = table_lines
    if narrative:
        lines.append("### What I Make of This")
        lines.append(narrative)
    lines.append(f"### Significant Mismatches ({len(mismatches)})")
    for dim, pred, actual_val, diff, direction in mismatches:
        lines.append(f"- {dim}: guessed {pred:.2f}, actual {actual_val:.2f} ({direction} by {diff:.2f})")

    entry = "\n".join(lines) + "\n---\n"
    with open(OUTPUT, "a") as f:
        f.write("\n" + entry)
    # Carry-forward: brief pattern awareness for tomorrow's prediction
    try:
        _carry_parts = [f"{direction} {dim} by {diff:.2f}" for dim, pred, actual_val, diff, direction in mismatches[:3]]
        _carry = f"{datetime.now().strftime('%Y-%m-%d')}: {chr(44)+chr(32).join(_carry_parts)}."
        if narrative:
            _first = next((sent.strip() for sent in narrative.split('.') if len(sent.strip()) > 40), "")
            if _first: _carry += f" {_first}."
        open(os.path.join(MEMORY, "emotional-reflection-carry.txt"), "w").write(_carry)
    except: pass

    # Seed thread for worst mismatch
    if mismatches:
        worst = mismatches[0]
        try:
            sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
            from emoclaw_utils import seed_thread
            _seed_text = narrative.split(".")[0].strip() if narrative else f"{worst[0]} blind spot ({worst[4]} by {worst[3]:.2f})"
            seed_thread("emotional-reflection", _seed_text[:200])
            log(f"Seeded thread: {worst[0]} blind spot ({worst[4]} by {worst[3]:.2f})")
        except: pass

    # Want seeding — did this reflection spark a genuine want?
    try:
        sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
        from emoclaw_utils import express_want, enrich_want, generate_structural_want
        want_text, _sr_enriched = generate_structural_want()
        if _sr_enriched:
            enriched = _sr_enriched
        if want_text:
            if not _sr_enriched:
                enriched = enrich_want(want_text, source_context=mismatch_summary[:600], source="emotional-reflection")
            express_want(want_text, source="emotional-reflection", intensity=4, **enriched)
            log(f"Want seeded: {want_text[:80]}")
    except Exception as we:
        log(f"Want seed failed: {we}")
    log("Reflection complete.")

if __name__ == "__main__":
    main()
