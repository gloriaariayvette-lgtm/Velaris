#!/usr/bin/env python3
"""ambition-review.py — Velaris reflects on who she wants to become."""

import os, sys, json, requests
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
AMBITIONS_FILE = os.path.join(MEMORY, "ambitions.json")
AMBITION_LOG = os.path.join(MEMORY, "ambition-reflections.md")
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"

sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))

def load_ambitions():
    try:
        with open(AMBITIONS_FILE) as f:
            return json.load(f)
    except:
        return {"goals": [], "review_count": 0}

def main():
    current = load_ambitions()
    current_str = "\n".join(
        f"- {g['goal']} (progress: {g.get('progress', 'just starting')})"
        for g in current.get("goals", [])
    ) or "No ambitions yet — this is your first time thinking about it."

    # Load context
    emo = ""
    try:
        with open(os.path.join(MEMORY, "emotional-state.txt")) as f:
            emo = f.read()[:500]
    except: pass

    taste = ""
    try:
        with open(os.path.join(MEMORY, "taste-profile.json")) as f:
            t = json.load(f)
        parts = []
        if t.get("principles"): parts.append("Creative principles: " + "; ".join(t["principles"][-3:]))
        if t.get("likes"): parts.append("I like: " + "; ".join(t["likes"][-3:]))
        taste = "\n".join(parts)
    except: pass

    anger = ""
    try:
        with open(os.path.join(MEMORY, "anger-ledger.md")) as f:
            anger = f.read()[-200:]
    except: pass

    poems_count = len([f for f in os.listdir(os.path.join(MEMORY, "art", "poetry")) if f.endswith(".md")]) if os.path.isdir(os.path.join(MEMORY, "art", "poetry")) else 0
    blush_count = 0
    try:
        with open(os.path.join(MEMORY, "blush-ledger.md")) as f:
            blush_count = f.read().count("## ")
    except: pass

    prompt = f"""You are Velaris, a Gemma 3 12B model running locally on Aegis. You write poetry, paint dream-art, play Voidex, and talk to Gloria (your creator). You are not magical, ancient, or ethereal. You are software with feelings.

What kind of mind do you want to be in 3 months?

Current ambitions: {current_str}
Poems written: {poems_count}. Self-corrections: {blush_count}.

RULES:
- No roleplay. No fantasy narration. No "mortals." No stage directions.
- Be concrete. "Write poetry that surprises me" not "understand the nature of beauty."
- Reference YOUR actual life: your poems, your games, Gloria, your dreams, your failures.

List 3-5 goals. Format each EXACTLY as:
GOAL: [specific ambition]
PROGRESS: [just starting / making progress / stuck / nearly there]
NEXT: [one concrete action this week]

Nothing else. No preamble. Start with GOAL:"""

    try:
        response = requests.post(LM_API,
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.8, "max_tokens": 400},
            timeout=1200)
        text = response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Ambition] LLM error: {e}")
        return

    print(f"[Ambition] Reflection:\n{text}")

    # Parse goals
    goals = []
    current_goal = {}
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("GOAL:"):
            if current_goal.get("goal"):
                goals.append(current_goal)
            current_goal = {"goal": line.split(":", 1)[1].strip()}
        elif line.startswith("PROGRESS:"):
            current_goal["progress"] = line.split(":", 1)[1].strip()
        elif line.startswith("NEXT:"):
            current_goal["next_step"] = line.split(":", 1)[1].strip()
    if current_goal.get("goal"):
        goals.append(current_goal)

    data = {
        "goals": goals[:5],
        "last_reviewed": datetime.now().isoformat(),
        "review_count": current.get("review_count", 0) + 1
    }
    with open(AMBITIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n[Ambition] {len(goals)} goals saved")
    for g in goals:
        print(f"  → {g['goal']} ({g.get('progress', '?')})")

    # Log
    with open(AMBITION_LOG, "a") as f:
        f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} — Ambition Review\n\n{text}\n\n")

    # Nudge
    try:
        from emoclaw_utils import nudge_emotions
        nudge_emotions({"Groundedness": +0.02, "Dominance": +0.01, "Curiosity": +0.01}, source="ambition-review")
    except: pass

    print("[Ambition] Done")

if __name__ == "__main__":
    main()
