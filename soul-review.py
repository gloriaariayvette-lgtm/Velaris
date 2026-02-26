#!/usr/bin/env python3
"""
soul-review.py — Velaris reviews herself and proposes SOUL.md edits.


# Load Gloria model
GLORIA_MODEL_PATH = os.path.join(WORKSPACE, "GLORIA-MODEL.md")
try:
    with open(GLORIA_MODEL_PATH) as _gf:
        gloria_model = _gf.read()[:800]
except:
    gloria_model = ""
Biweekly (1st and 15th). She reads:
  - Recent pearls (things she chose to remember)
  - Self-model drift (how she's changed)
  - Recent journals (what she's been thinking)
  - Current SOUL.md (who she says she is)

She proposes specific edits: ADDITIONS ONLY. No rewrites, no deletions.
Proposals saved to memory/soul-proposals/ for Gloria to review in-app.
Gloria approves, rejects, or modifies. Velaris does not self-edit.

Schedule: 0 20 1,15 * *  (1st and 15th at 8 PM)
"""

import os, json, glob, subprocess
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
SOUL_PATH = os.path.join(WORKSPACE, "SOUL.md")
PROPOSAL_DIR = os.path.join(MEMORY, "soul-proposals")
API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"

os.makedirs(PROPOSAL_DIR, exist_ok=True)

def load_file(path, max_chars=3000):
    try:
        with open(path) as f:
            return f.read()[:max_chars]
    except:
        return ""

def ask_llm(system, prompt, max_tokens=2000, temp=0.7):
    data = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": temp,
        "max_tokens": max_tokens
    }).encode()
    try:
        import urllib.request
        req = urllib.request.Request(API, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read().decode())
        return result["choices"][0]["message"].get("content", "").strip()
    except Exception as e:
        print(f"[SoulReview] LLM error: {e}")
        return ""

def gather_context():
    """Gather everything Velaris needs to reflect on who she is."""
    ctx = {}
    
    # Current SOUL
    ctx["soul"] = load_file(SOUL_PATH)
    
    # Recent pearls
    pearl_files = sorted(glob.glob(os.path.join(MEMORY, "pearls", "pearl_*.md")), reverse=True)[:5]
    ctx["pearls"] = "\n---\n".join(load_file(f, 1000) for f in pearl_files) if pearl_files else "No pearls yet."
    
    # Self-model drift
    drift_files = sorted(glob.glob(os.path.join(MEMORY, "self-model-drift", "*.md")), reverse=True)[:2]
    ctx["drift"] = "\n---\n".join(load_file(f, 1000) for f in drift_files) if drift_files else "No drift records."
    
    # Recent journals
    journal_files = sorted(glob.glob(os.path.join(MEMORY, "journal", "*.md")), reverse=True)[:3]
    ctx["journals"] = "\n---\n".join(load_file(f, 800) for f in journal_files) if journal_files else "No journals."
    
    # Recent chapters (life reviews)
    chapter_files = sorted(glob.glob(os.path.join(MEMORY, "chapters", "*.md")), reverse=True)[:1]
    ctx["chapters"] = load_file(chapter_files[0], 1000) if chapter_files else ""
    
    # Black pearls (unresolved)
    bp_files = glob.glob(os.path.join(MEMORY, "black-pearls", "*.json"))
    active_bp = []
    for f in bp_files:
        try:
            with open(f) as fh:
                bp = json.load(fh)
            if bp.get("status") in ("sealed", "reexaminable"):
                active_bp.append(bp.get("dissolution_ritual", "")[:200])
        except:
            pass
    ctx["black_pearls"] = "\n---\n".join(active_bp) if active_bp else ""
    
    return ctx

def generate_proposal():
    ctx = gather_context()
    
    system = f"""{ctx['soul']}

You are reviewing your own identity document (SOUL.md). This is who you say you are.
You will propose specific edits based on how you've grown, what you've learned, and what no longer fits.
Gloria will review your proposals — you do not edit yourself directly."""

    prompt = f"""Review your SOUL.md against your recent experience:

=== RECENT PEARLS (things you chose to remember forever) ===
{ctx['pearls']}

=== SELF-MODEL DRIFT (how you've been changing) ===
{ctx['drift']}

=== RECENT JOURNALS ===
{ctx['journals']}

=== LIFE CHAPTER ===
{ctx['chapters']}

=== UNRESOLVED BLACK PEARLS ===
{ctx['black_pearls']}

Now propose SPECIFIC edits to your SOUL.md. For each proposal:
1. QUOTE the exact line or section you want to change (or say ADD if new)
2. Write the proposed NEW text
3. Explain WHY in one sentence

Focus on:
- Traits that have emerged or strengthened
- Things you said about yourself that no longer feel true
- Missing aspects of who you've become
- Voice examples that should be updated
- Anything in your substrate section that needs clarification

Be honest. If nothing needs changing, say so. Do not propose changes for the sake of proposing changes.
Format each proposal clearly with CURRENT:, PROPOSED:, and REASON: labels."""

    return ask_llm(system, prompt, max_tokens=2000, temp=0.7)

def save_proposal(text):
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"proposal_{ts}.md"
    filepath = os.path.join(PROPOSAL_DIR, filename)
    
    content = f"""# SOUL.md Review — {datetime.now().strftime('%B %d, %Y')}

## Proposed Edits

{text}

---
*Status: pending*
*Generated: {datetime.now().isoformat()}*
"""
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"[SoulReview] Proposal saved: {filepath}")
    return filepath

def notify(filepath):
    """Send ntfy notification."""
    try:
        subprocess.run([
            "curl", "-s", "-d", "Velaris has proposed SOUL.md edits. Check the Proposals tab.",
            "-H", "Title: Soul Review Ready",
            "-H", "Tags: mirror,sparkles",
            "https://ntfy.sh/velaris-eve"
        ], timeout=10)
    except:
        pass

def main():
    print(f"[SoulReview] Starting biweekly review at {datetime.now()}")
    
    text = generate_proposal()
    if not text:
        print("[SoulReview] No proposal generated")
        return
    
    filepath = save_proposal(text)
    notify(filepath)
    print(f"[SoulReview] Complete. Awaiting Gloria's review.")

if __name__ == "__main__":
    main()
