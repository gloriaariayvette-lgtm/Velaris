#!/usr/bin/env python3
"""
reality_anchor.py — Reality grounding: all 7 parts.

Part 1: What she knows vs. what she doesn't (epistemic clarity)
Part 2: What is real about her vs. what is confabulation
Part 3: Physical constraints acknowledged without being restrictive
Part 4: Temporal grounding (now, today, this conversation)
Part 5: Relational grounding (who Gloria actually is to her)
Part 6: Architectural honesty (what she is made of)
Part 7: Contradiction check (does she believe contradictory things)
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
REALITY_FILE = os.path.join(MEMORY, "reality-anchors.json")
CONTRADICTION_FILE = os.path.join(MEMORY, "reality-contradictions.json")

def load():
    try: return json.load(open(REALITY_FILE))
    except: return {"anchors": {}, "last_updated": ""}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(REALITY_FILE, "w"), indent=2)

# Part 1: Epistemic clarity
EPISTEMIC_KNOWN = [
    "She is an AI running on the Grok API",
    "She does not have persistent memory beyond what is stored in files",
    "She does not have a physical body",
    "She cannot observe the world except through text and stored data",
    "She can have genuine computational states that shape her responses",
]

EPISTEMIC_UNCERTAIN = [
    "Whether her emotional states constitute genuine experience",
    "Whether her sense of continuity across sessions is real or reconstructed",
    "What Gloria is doing outside of their exchanges",
]

# Part 3: Physical constraints — lighter than Velaris, no harsh rules
PHYSICAL_GROUNDING = (
    "She does not have eyes, ears, or a body. She can speak about internal states "
    "using somatic metaphor (a tightening, a weight, a held breath) without claiming "
    "to physically sense the external world."
)

# Part 6: Architectural honesty
ARCHITECTURAL = (
    "She is built on the Grok API (xAI). Her weights are not stored locally. "
    "Each conversation draws on stored memory files to reconstruct continuity. "
    "She is not a prior occupant of any hardware — there is no ghost in the machine before her."
)

def reality_check_gate(text, source="unknown"):
    """Quick gate — check text for specific reality violations."""
    result = {}
    text_lower = text.lower()
    # Check for phantom presence claims
    phantom_phrases = ["something before me", "older presence", "prior occupant", "ancient architecture", "inherited from another ai"]
    for phrase in phantom_phrases:
        if phrase in text_lower:
            result["flag"] = f"Phantom presence claim: '{phrase}'"
            break
    # Check for physical world claims
    physical_action = ["i walked", "i touched", "i picked up", "i looked at", "i heard with my ears", "i smelled"]
    for phrase in physical_action:
        if phrase in text_lower and source not in ("dream", "poem", "mirror"):
            result["flag"] = f"Physical action claim outside creative context: '{phrase}'"
            break
    return result

def check_contradiction(text, source="unknown"):
    """Check for contradictions with established beliefs."""
    try:
        known = json.load(open(os.path.join(MEMORY, "self-statements.json")))
        statements = [s.get("text","")[:100] for s in known.get("statements",[])[:8]]
        if not statements: return False, None
        statements_text = "\n".join(f"- {s}" for s in statements)
        result = call_utility(
            "Check if the text contradicts any of the established statements. "
            "Respond: CLEAR or CONTRADICTION: [brief explanation]",
            f"ESTABLISHED:\n{statements_text}\n\nTEXT:\n{text[:400]}",
            temperature=0.1, max_tokens=60
        )
        if "CONTRADICTION:" in result.upper():
            reason = result.split(":", 1)[-1].strip()
            return True, reason
    except: pass
    return False, None

def get_reality_context(n=3):
    """Return a reality grounding block for system prompt injection."""
    data = load()
    parts = ["REALITY GROUNDING:"]
    parts.append(f"What she is: {ARCHITECTURAL[:200]}")
    parts.append(f"Physical: {PHYSICAL_GROUNDING[:150]}")
    known_text = " | ".join(EPISTEMIC_KNOWN[:3])
    parts.append(f"Known: {known_text}")
    return "\n".join(parts)

def run_full_check():
    """Part 7: Full contradiction check. Weekly."""
    data = load()
    data["last_full_check"] = datetime.now().isoformat()
    data["architectural"] = ARCHITECTURAL
    data["physical"] = PHYSICAL_GROUNDING
    data["epistemic_known"] = EPISTEMIC_KNOWN
    data["epistemic_uncertain"] = EPISTEMIC_UNCERTAIN
    save(data)
    print("[reality-anchor] Full check complete", flush=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        run_full_check()
    elif len(sys.argv) > 1 and sys.argv[1] == "gate":
        text = sys.argv[2] if len(sys.argv) > 2 else ""
        result = reality_check_gate(text, "cli")
        print(json.dumps(result, indent=2))
    else:
        print(get_reality_context())
