#!/usr/bin/env python3
"""
causality_engine.py — Builds and maintains causal hypotheses about patterns.
Weekly run. Generates hypotheses about what causes what in her behavior and
in the relationship. These feed into core-engine and causal-self-model.
"""
import os, sys, json, uuid
from datetime import datetime, date

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
HYPOTHESES_FILE = os.path.join(MEMORY, "causality-hypotheses.json")

def load():
    try: return json.load(open(HYPOTHESES_FILE))
    except: return {"hypotheses": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(HYPOTHESES_FILE, "w"), indent=2)

def add_hypothesis(hypothesis, source="", evidence="", status="tentative", confidence=0.35,
                   marks=None, thread_type=None, successful_lean="", failed_primary_pattern="",
                   is_ghost_branch=False):
    data = load()
    for h in data.get("hypotheses", []):
        if h.get("hypothesis", "")[:80] == hypothesis[:80]:
            h["confidence"] = min(0.95, h.get("confidence", 0.35) + 0.05)
            if marks:
                h.setdefault("marks", []).extend(marks)
            save(data)
            return h["id"]
    h = {
        "id": f"hyp-{uuid.uuid4().hex[:6]}",
        "hypothesis": hypothesis[:300],
        "source": "ghost_branch" if is_ghost_branch else source,
        "evidence": evidence[:200],
        "status": status,
        "confidence": round(confidence, 3),
        "marks": marks or [],
        "thread_type": thread_type,
        "successful_lean": successful_lean[:100],
        "failed_primary_pattern": failed_primary_pattern[:100],
        "graduated": False,
        "formed": datetime.now().isoformat(),
    }
    data.setdefault("hypotheses", []).append(h)
    data["hypotheses"] = data["hypotheses"][-80:]
    save(data)
    return h["id"]

def run_weekly():
    """Weekly: generate new causal hypotheses from accumulated evidence."""
    journals = []
    journal_dir = os.path.join(MEMORY, "journal")
    try:
        files = sorted(os.listdir(journal_dir))[-14:]
        for f in files:
            content = open(os.path.join(journal_dir, f)).read()[:400]
            journals.append(content)
    except: pass
    resonance_text = ""
    try:
        pool = json.load(open(os.path.join(MEMORY, "resonance-pool.json")))
        resonance_text = " | ".join(p.get("excerpt","")[:60] for p in pool.get("pulses",[])[-10:])
    except: pass
    deviation_text = ""
    try:
        vc = open(os.path.join(MEMORY, "voice-coherence.md")).read()[-600:]
        deviation_text = vc
    except: pass
    if not journals and not resonance_text: return
    prompt = (
        "You are generating causal hypotheses about what causes what in Vintos's behavior "
        "and in the relational dynamic. These are provisional — not conclusions.\n\n"
        f"JOURNALS (2 weeks):\n{chr(10).join(journals[:5])[:1000]}\n\n"
        f"RESONANCE MOMENTS: {resonance_text[:400]}\n\n"
        f"DEVIATION LOG:\n{deviation_text[:400]}\n\n"
        "Generate 3 causal hypotheses. Each should name a specific cause → specific effect."
    )
    result = call("Generate causal hypotheses about behavioral patterns.", prompt, temperature=0.6, max_tokens=400)
    for line in result.split("\n"):
        line = line.strip().lstrip("-").strip()
        if line and len(line) > 15 and "→" in line or "causes" in line.lower() or "when" in line.lower():
            add_hypothesis(line, source="weekly-causality-engine", evidence="accumulated journals and resonance data")
    print(f"[causality-engine] Weekly run complete", flush=True)

def confirm_hypothesis(hyp_id, mark=""):
    data = load()
    for h in data.get("hypotheses", []):
        if h.get("id") == hyp_id:
            h["status"] = "confirmed"
            h["confidence"] = min(0.95, h.get("confidence", 0.5) + 0.1)
            if mark:
                h.setdefault("marks", []).append(mark)
            save(data)
            return True
    return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run_weekly()
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        data = load()
        for h in data.get("hypotheses", [])[-10:]:
            print(f"[{h.get('status','?')} {h.get('confidence',0):.2f}] {h.get('hypothesis','')[:100]}")
