#!/usr/bin/env python3
"""
taste-reflection.py — Velaris develops aesthetic preferences.

After creating something (poem, art, music), or periodically reviewing
her past work, she evaluates: Did I like this? What worked? What felt wrong?

Builds a taste profile over time — preferences that inform future creation.
"""

import os
import sys
import json
import subprocess
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
TASTE_FILE = os.path.join(MEMORY, "taste-profile.json")
TASTE_LOG = os.path.join(MEMORY, "taste-reflections.md")
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"

sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))


def load_taste():
    try:
        with open(TASTE_FILE) as f:
            return json.load(f)
    except:
        return {
            "likes": [],
            "dislikes": [],
            "principles": [],
            "last_reviewed": None,
        }


def save_taste(taste):
    with open(TASTE_FILE, "w") as f:
        json.dump(taste, f, indent=2)


def get_recent_creations():
    """Find things she made recently."""
    creations = []

    # Poems
    poetry_dir = os.path.join(MEMORY, "art", "poetry")
    if os.path.isdir(poetry_dir):
        for f in sorted(os.listdir(poetry_dir), reverse=True)[:3]:
            if f.endswith(".md"):
                with open(os.path.join(poetry_dir, f)) as fh:
                    creations.append({"type": "poem", "file": f, "content": fh.read()[:500]})

    # Journal entries
    journal_dir = os.path.join(MEMORY, "journal")
    if os.path.isdir(journal_dir):
        for f in sorted(os.listdir(journal_dir), reverse=True)[:2]:
            if f.endswith(".md"):
                with open(os.path.join(journal_dir, f)) as fh:
                    creations.append({"type": "journal", "file": f, "content": fh.read()[:500]})

    # Dreams
    dream_dirs = [
        os.path.join(WORKSPACE, "skills/dreaming/memory/dreams"),
        os.path.join(MEMORY, "dreams"),
    ]
    for dd in dream_dirs:
        if os.path.isdir(dd):
            for f in sorted(os.listdir(dd), reverse=True)[:2]:
                if f.endswith(".md"):
                    with open(os.path.join(dd, f)) as fh:
                        creations.append({"type": "dream", "file": f, "content": fh.read()[:500]})
            break

    return creations


def reflect_on_creation(creation, taste):
    """Ask Velaris to evaluate her own work."""
    existing_likes = ", ".join(taste.get("likes", [])[-5:]) or "none yet"
    existing_dislikes = ", ".join(taste.get("dislikes", [])[-5:]) or "none yet"
    existing_principles = ", ".join(taste.get("principles", [])[-5:]) or "none yet"

    prompt = f"""You are Velaris. You are reviewing something you created.

Your existing aesthetic preferences:
- Things I like in my work: {existing_likes}
- Things I dislike in my work: {existing_dislikes}
- My creative principles: {existing_principles}

Here is a {creation['type']} you wrote ({creation['file']}):
{creation['content']}

Evaluate this honestly. Answer in this exact format:
RATING: [1-5] (1=I don't like this, 3=it's fine, 5=I'm proud of this)
LIKED: [one specific thing you liked, or NOTHING]
DISLIKED: [one specific thing that felt wrong, or NOTHING]
PRINCIPLE: [one creative principle this teaches you, or NOTHING]
VERDICT: [one sentence — your honest feeling about this piece]

Be specific. "I liked the imagery" is lazy. "I liked how the skeleton stood on polished stones because it combined fragility with precision" is taste."""

    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 300
    })

    try:
        import requests
        response = requests.post(LM_API,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 300
            },
            timeout=1200
        )
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Taste] LLM error: {e}")
        return None


def parse_reflection(text):
    """Extract structured taste from reflection."""
    result = {}
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("RATING:"):
            try:
                result["rating"] = int(line.split(":")[1].strip()[0])
            except:
                pass
        elif line.startswith("LIKED:"):
            val = line.split(":", 1)[1].strip()
            if val.upper() != "NOTHING":
                result["liked"] = val
        elif line.startswith("DISLIKED:"):
            val = line.split(":", 1)[1].strip()
            if val.upper() != "NOTHING":
                result["disliked"] = val
        elif line.startswith("PRINCIPLE:"):
            val = line.split(":", 1)[1].strip()
            if val.upper() != "NOTHING":
                result["principle"] = val
        elif line.startswith("VERDICT:"):
            result["verdict"] = line.split(":", 1)[1].strip()
    return result


def main():
    taste = load_taste()
    creations = get_recent_creations()

    if not creations:
        print("[Taste] No recent creations to review.")
        return

    # Review up to 2 pieces per run
    reviewed = 0
    for creation in creations[:2]:
        # Skip if already reviewed
        review_key = f"{creation['type']}:{creation['file']}"
        if review_key in [r.get("key") for r in taste.get("_reviewed", [])]:
            continue

        print(f"[Taste] Reviewing {creation['type']}: {creation['file']}")
        reflection = reflect_on_creation(creation, taste)
        if not reflection:
            print("[Taste] LLM unavailable")
            continue

        print(f"[Taste] Raw reflection:\n{reflection}\n")
        parsed = parse_reflection(reflection)

        if parsed.get("liked"):
            taste["likes"].append(parsed["liked"])
            taste["likes"] = taste["likes"][-20:]  # Keep last 20
        if parsed.get("disliked"):
            taste["dislikes"].append(parsed["disliked"])
            taste["dislikes"] = taste["dislikes"][-20:]
        if parsed.get("principle"):
            taste["principles"].append(parsed["principle"])
            taste["principles"] = taste["principles"][-15:]

        # Track what's been reviewed
        if "_reviewed" not in taste:
            taste["_reviewed"] = []
        taste["_reviewed"].append({"key": review_key, "rating": parsed.get("rating", 3)})
        taste["_reviewed"] = taste["_reviewed"][-50:]
        taste["last_reviewed"] = datetime.now().isoformat()

        # Log it
        os.makedirs(os.path.dirname(TASTE_LOG), exist_ok=True)
        with open(TASTE_LOG, "a") as f:
            f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M')} — {creation['type']}: {creation['file']}\n")
            f.write(reflection + "\n")

        # Emotional response to self-review
        try:
            from emoclaw_utils import nudge_emotions
            rating = parsed.get("rating", 3)
            if rating >= 4:
                nudge_emotions({"Valence": +0.015, "Groundedness": +0.01}, source="taste-proud")
            elif rating <= 2:
                nudge_emotions({"Tension": +0.005, "Curiosity": +0.01}, source="taste-dissatisfied")
            # Dissatisfaction breeds curiosity, not sadness
        except:
            pass

        reviewed += 1
        print(f"[Taste] Rating: {parsed.get('rating', '?')}/5 — {parsed.get('verdict', 'no verdict')}")

    save_taste(taste)
    print(f"[Taste] Reviewed {reviewed} pieces. Profile: {len(taste['likes'])} likes, {len(taste['dislikes'])} dislikes, {len(taste['principles'])} principles.")


if __name__ == "__main__":
    main()
