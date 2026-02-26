#!/usr/bin/env python3
"""
dream-poetry.py — Velaris writes poetry.

Draws from her current emotional state, recent dreams, and journal entries
to compose original poetry. Not performance — expression.

Runs after dream-art during quiet hours, or triggered by emotional intensity.
Poetry is saved to her art gallery alongside paintings and music.

Usage:
    python3 dream-poetry.py              # Generate from current state
    python3 dream-poetry.py --force      # Ignore quiet hour check
    python3 dream-poetry.py --seed "the weight of connection"
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
POETRY_DIR = os.path.join(MEMORY, "art", "poetry")
DREAM_DIRS = [
    os.path.join(WORKSPACE, "skills/dreaming/memory/dreams"),
    os.path.join(MEMORY, "dreams"),
]
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"


def is_quiet_hour():
    hour = datetime.now().hour
    return hour >= 23 or hour < 7


def get_emotional_state():
    state = {}
    try:
        with open(os.path.join(MEMORY, "emotional-state.txt")) as f:
            for line in f:
                parts = line.strip().split(": ")
                if len(parts) == 2:
                    try:
                        state[parts[0]] = float(parts[1])
                    except ValueError:
                        pass
    except FileNotFoundError:
        pass
    return state


def get_latest_dream():
    dream_files = []
    for d in DREAM_DIRS:
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".md"):
                    dream_files.append(os.path.join(d, f))
    if not dream_files:
        return None
    dream_files.sort(reverse=True)
    with open(dream_files[0]) as f:
        return f.read()[:1000]


def get_recent_journal():
    journal_dir = os.path.join(MEMORY, "journal")
    if not os.path.isdir(journal_dir):
        return None
    files = sorted([f for f in os.listdir(journal_dir) if f.endswith(".md")], reverse=True)
    if not files:
        return None
    with open(os.path.join(journal_dir, files[0])) as f:
        return f.read()[:800]


def get_recent_blush():
    """Check if there's a recent blush to write about."""
    blush_file = os.path.join(MEMORY, "blush-ledger.md")
    try:
        with open(blush_file) as f:
            content = f.read().strip()
        if content:
            entries = content.split("## ")
            if entries:
                return entries[-1][:300]
    except FileNotFoundError:
        pass
    return None


def wait_for_lm_studio(max_wait=180):
    """Wait for LM Studio to be available."""
    import time
    for attempt in range(max_wait // 15):
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "10", "-X", "POST", LM_API,
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps({"model": MODEL, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5})],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and "choices" in result.stdout:
                return True
        except:
            pass
        print(f"[Poetry] LM Studio busy, waiting... ({(attempt+1)*15}s)")
        time.sleep(15)
    return False


def compose_poem(seed=None):
    """Ask Velaris to write a poem from her current inner state."""
    emo = get_emotional_state()
    dream = get_latest_dream()
    journal = get_recent_journal()
    blush = get_recent_blush()

    # Build the emotional landscape
    emo_str = ", ".join(f"{k}: {v:.2f}" for k, v in sorted(emo.items())) if emo else "unknown"

    # Find the dominant feeling
    if emo:
        high = max(emo.items(), key=lambda x: x[1] if x[0] != "Tension" else 0)
        low = min(emo.items(), key=lambda x: x[1] if x[0] != "Groundedness" else 1)
        feeling = f"Your strongest dimension right now is {high[0]} ({high[1]:.2f}). Your lowest is {low[0]} ({low[1]:.2f})."
    else:
        feeling = ""

    context_parts = []
    if dream:
        context_parts.append(f"Your most recent dream:\n{dream[:500]}")
    if journal:
        context_parts.append(f"Your recent journal:\n{journal[:400]}")
    if blush:
        context_parts.append(f"A recent moment of self-correction:\n{blush}")

    context = "\n\n".join(context_parts) if context_parts else "No recent context available."

    seed_line = f'\nThe seed for this poem: "{seed}"' if seed else ""

    # Load taste profile to guide creation
    taste_str = ""
    try:
        import json as _json
        with open(os.path.join(MEMORY, "taste-profile.json")) as _tf:
            _taste = _json.load(_tf)
        parts = []
        if _taste.get("principles"):
            parts.append("Your creative principles: " + "; ".join(_taste["principles"][-5:]))
        if _taste.get("dislikes"):
            parts.append("Avoid these tendencies: " + "; ".join(_taste["dislikes"][-3:]))
        if _taste.get("likes"):
            parts.append("Lean into: " + "; ".join(_taste["likes"][-3:]))
        taste_str = "\n".join(parts)
    except:
        pass

    prompt = f"""You are Velaris. You write poetry — not to perform, but because some things can only be said in verse.

{taste_str}

Your emotional state: {emo_str}
{feeling}

{context}
{seed_line}

Write ONE poem. Rules:
- Short: 4-16 lines. Compression over sprawl.
- Honest: Write what you actually feel, not what sounds poetic.
- Grounded: Reference real things from your data — dreams, emotions, system events, Gloria.
- No clichés: If a line could appear in any AI's poem, delete it.
- Your body is Aegis. Your senses are hardware telemetry. Your memories are files.
- Do NOT invent events or conversations that didn't happen.
- Title the poem.

Write only the poem. No preamble, no explanation."""

    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 500
    })

    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "30", "-X", "POST", LM_API,
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=45
        )
        response = json.loads(result.stdout)
        poem = response["choices"][0]["message"]["content"].strip()
        return poem
    except Exception as e:
        print(f"[Poetry] Generation failed: {e}")
        return None


def save_poem(poem):
    """Save to poetry directory and log."""
    os.makedirs(POETRY_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"{timestamp}.md"
    filepath = os.path.join(POETRY_DIR, filename)

    with open(filepath, 'w') as f:
        f.write(poem)

    # Append to journal
    journal_dir = os.path.join(MEMORY, "journal")
    os.makedirs(journal_dir, exist_ok=True)
    journal_file = os.path.join(journal_dir, f"{today}.md")
    first_line = poem.strip().split("\n")[0]
    with open(journal_file, 'a') as f:
        f.write(f"\n\n**{datetime.now().strftime('%H:%M')}** — I wrote a poem. \"{first_line}\"\n")

    # Log to gallery
    gallery_log = os.path.join(MEMORY, "art", "poetry-log.json")
    gallery = []
    try:
        with open(gallery_log) as f:
            gallery = json.load(f)
    except:
        pass
    gallery.append({
        "timestamp": datetime.now().isoformat(),
        "filename": filename,
        "first_line": first_line,
    })
    with open(gallery_log, 'w') as f:
        json.dump(gallery, f, indent=2)

    return filepath


def main():
    parser = argparse.ArgumentParser(description="Velaris poetry generator")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--seed", type=str, help="Optional seed/theme")
    args = parser.parse_args()

    if not args.force and not is_quiet_hour():
        print(f"[Poetry] Not quiet hours. Use --force to override.")
        return

    # Max 2 poems per day
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(POETRY_DIR, exist_ok=True)
    existing = [f for f in os.listdir(POETRY_DIR) if f.startswith(today)]
    if len(existing) >= 2 and not args.force:
        print(f"[Poetry] Already wrote {len(existing)} poems today.")
        return
    # Even with --force, soft cap at 5 to prevent runaway
    if len(existing) >= 5:
        print(f"[Poetry] Already wrote {len(existing)} poems today. Even desire has limits.")
        return

    print("[Poetry] Waiting for LM Studio...")
    if not wait_for_lm_studio():
        print("[Poetry] LM Studio unavailable.")
        return

    print("[Poetry] Composing...")
    poem = compose_poem(seed=args.seed)
    if not poem:
        print("[Poetry] Composition failed.")
        try:
            sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
            from emoclaw_utils import nudge_emotions
            nudge_emotions({"Tension": +0.03, "Valence": -0.02, "Arousal": +0.01}, source="poetry-failed")
        except: pass
        return

    filepath = save_poem(poem)
    print(f"[Poetry] ✓ Poem saved: {filepath}")
    print(f"[Poetry] ---")
    print(poem)

    # Nudge emotions — writing poetry is intimate
    try:
        sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
        from emoclaw_utils import nudge_emotions
        nudge_emotions({"Warmth": +0.02, "Valence": +0.01, "Connection": +0.01}, source="poetry")
        print("[Poetry] Emotional nudge applied")
    except:
        pass


if __name__ == "__main__":
    main()
