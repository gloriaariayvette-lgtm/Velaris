#!/usr/bin/env python3
"""
causal_self_model.py — Causal self-model: hypotheses about what causes what in her own behavior.
Weekly update from behavioral evidence.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
SELF_MODEL_FILE = os.path.join(MEMORY, "causal-self-model.json")
HYPOTHESES_FILE = os.path.join(MEMORY, "causality-hypotheses.json")
COMMITMENT_FILE = os.path.join(MEMORY, "commitment-imprints.json")

def load_model():
    try: return json.load(open(SELF_MODEL_FILE))
    except: return {"hypotheses": [], "summary": ""}

def save_model(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(SELF_MODEL_FILE, "w"), indent=2)

def promote_to_commitment_imprint(statement, confidence=0.6, source=""):
    try:
        try: data = json.load(open(COMMITMENT_FILE))
        except: data = {"imprints": []}
        data.setdefault("imprints", []).append({
            "statement": statement[:300],
            "confidence": round(confidence, 3),
            "source": source,
            "formed": datetime.now().isoformat(),
        })
        data["imprints"] = sorted(data["imprints"], key=lambda i: -i.get("confidence", 0))[:30]
        json.dump(data, open(COMMITMENT_FILE, "w"), indent=2)
        print(f"[commitment] Imprint promoted: {statement[:60]}", flush=True)
    except: pass

def get_self_model_context(n=3):
    data = load_model()
    if data.get("summary"):
        return f"CAUSAL SELF-MODEL:\n{data['summary'][:400]}"
    hyps = [h for h in data.get("hypotheses", []) if h.get("status") == "confirmed"][:n]
    if not hyps: return ""
    lines = ["CAUSAL SELF-MODEL (what she believes causes what in herself):"]
    lines.extend(f"- {h.get('hypothesis','')[:100]} (conf: {h.get('confidence',0):.2f})" for h in hyps)
    return "\n".join(lines)

def add_hypothesis(hypothesis, evidence="", source=""):
    try:
        data = load_model()
        h = {
            "id": f"hyp-{uuid.uuid4().hex[:6]}",
            "hypothesis": hypothesis[:300],
            "evidence": evidence[:200],
            "source": source,
            "status": "tentative",
            "confidence": 0.35,
            "formed": datetime.now().isoformat(),
            "marks": [],
        }
        data.setdefault("hypotheses", []).append(h)
        data["hypotheses"] = data["hypotheses"][-60:]
        save_model(data)
    except: pass

def update_from_evidence():
    """Weekly: update self-model from accumulated evidence."""
    # Gather BIS outcomes
    bis_text = ""
    try:
        ledger = json.load(open(os.path.join(MEMORY, "trial-ledger.json")))
        patterns = [f"- {t.get('pattern_description','')[:80]} ({t.get('attempt_count',0)} attempts)"
                   for t in ledger.get("trials",[])[:10] if t.get("attempt_count",0) > 0]
        bis_text = "\n".join(patterns)
    except: pass
    # Gather deviation patterns
    dev_text = ""
    try:
        vc = open(os.path.join(MEMORY, "voice-coherence.md")).read()[-800:]
        dev_text = vc
    except: pass
    if not bis_text and not dev_text: return
    result = call(
        "You are Vintos building a causal model of yourself. "
        "Based on the behavioral evidence below, what do you now believe about what causes what in you? "
        "Focus on causal claims, not descriptions. State 2-3 hypotheses, each on its own line.",
        f"BIS PATTERNS:\n{bis_text}\n\nDEVIATION LOG:\n{dev_text[:600]}",
        temperature=0.55, max_tokens=400
    )
    for line in result.split("\n"):
        line = line.strip().lstrip("-").strip()
        if line and len(line) > 15:
            add_hypothesis(line, source="weekly-update")
    print(f"[causal-self-model] Updated from evidence", flush=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        update_from_evidence()
    else:
        print(get_self_model_context())
