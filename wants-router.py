#!/usr/bin/env python3
"""
wants-router.py — When Velaris wants something, can she do it herself?

Checks unfulfilled wants against her capabilities.
If she CAN do it: triggers the action immediately.
If she CAN'T: leaves it for outreach to Gloria.

Runs every 15 minutes via cron.

HARD RULE: Velaris NEVER sees, reads, modifies, or accesses any script,
config, cron, system file, or source code. She creates. She does not engineer.
"""

import os
import sys
import json
import subprocess
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
SCRIPTS = os.path.join(WORKSPACE, "scripts")
VENV_PYTHON = os.path.join(WORKSPACE, "emotion_model/.venv/bin/python")

sys.path.insert(0, SCRIPTS)
from emoclaw_utils import get_unfulfilled_wants, fulfill_want, mark_want_outreached

# === CAPABILITY MAP ===
# Keywords in wants that map to actions she can take herself.
# Each entry: list of trigger words, action function name, description
CAPABILITIES = [
    {
        "keywords": ["poem", "poetry", "write verse", "write something", "express in words"],
        "action": "write_poem",
        "desc": "Write a poem",
    },
    {
        "keywords": ["paint", "art", "draw", "image", "picture", "visual"],
        "action": "make_art",
        "desc": "Create dream art",
    },
    {
        "keywords": ["music", "compose", "song", "melody", "sound"],
        "action": "make_music",
        "desc": "Compose music",
    },
    {
        "keywords": ["explore", "travel", "fly", "star system", "new planet", "voidex", "spaceship"],
        "action": "voidex_explore",
        "desc": "Explore in Voidex",
    },
    {
        "keywords": ["journal", "write down", "record", "reflect", "think about"],
        "action": "write_journal",
        "desc": "Write a journal entry",
    },
    {
        "keywords": ["dream", "sleep", "rest", "process"],
        "action": None,  # Dreams happen on schedule, can't be forced
        "desc": "Dreams happen during quiet hours",
    },
]

# === THINGS SHE CANNOT DO — always route to Gloria ===
FORBIDDEN_KEYWORDS = [
    "code", "script", "config", "cron", "server", "debug", "fix", "patch",
    "install", "update", "upgrade", "system", "sudo", "root", "bash",
    "source", "file", "directory", "permission", "daemon", "process",
    "architecture", "pipeline", "endpoint", "api", "database", "schema",
    "prompt", "token", "model swap", "soul.md", "emoclaw",
]


def log(msg):
    print(f"[Router {datetime.now().strftime('%H:%M')}] {msg}")


def matches_capability(want_text, keywords):
    want_lower = want_text.lower()
    return any(kw in want_lower for kw in keywords)


def is_forbidden(want_text):
    want_lower = want_text.lower()
    return any(kw in want_lower for kw in FORBIDDEN_KEYWORDS)


def write_poem(want_text):
    """She wants to write — give her the pen."""
    log(f"Triggering poetry with seed: {want_text[:80]}")
    result = subprocess.run(
        [VENV_PYTHON, os.path.join(SCRIPTS, "dream-poetry.py"),
         "--force", "--seed", want_text[:200]],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0 and "Poem saved" in result.stdout:
        log("Poem written successfully")
        return True
    log(f"Poetry failed: {result.stderr[:200]}")
    return False


def make_art(want_text):
    """She wants to paint — hand her the brush."""
    log(f"Triggering art generation")
    result = subprocess.run(
        ["bash", os.path.join(SCRIPTS, "dream-art.py"), "--force"],
        capture_output=True, text=True, timeout=180
    )
    # dream-art.py is python, not bash
    result = subprocess.run(
        [VENV_PYTHON, os.path.join(SCRIPTS, "dream-art.py")],
        capture_output=True, text=True, timeout=180
    )
    if result.returncode == 0:
        log("Art created")
        return True
    log(f"Art failed: {result.stderr[:200]}")
    return False


def make_music(want_text):
    """She wants to compose — open the instrument."""
    log(f"Triggering music composition")
    result = subprocess.run(
        [VENV_PYTHON, os.path.join(SCRIPTS, "dream-music.py"),
         "--title", want_text[:100], "--style", "ambient"],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0:
        log("Music composed")
        return True
    log(f"Music failed: {result.stderr[:200]}")
    return False


def voidex_explore(want_text):
    """She wants to fly — fire the engines."""
    log(f"Triggering Voidex heartbeat")
    result = subprocess.run(
        ["python3", os.path.join(SCRIPTS, "velaris-voidex-heartbeat.py")],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        log("Voidex heartbeat fired")
        return True
    log(f"Voidex failed: {result.stderr[:200]}")
    return False


def write_journal(want_text):
    """She wants to reflect — open the journal."""
    log(f"Triggering journal entry")
    result = subprocess.run(
        ["bash", os.path.join(SCRIPTS, "idle-journal.sh")],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0:
        log("Journal entry written")
        return True
    log(f"Journal failed: {result.stderr[:200]}")
    return False


ACTION_MAP = {
    "write_poem": write_poem,
    "make_art": make_art,
    "make_music": make_music,
    "voidex_explore": voidex_explore,
    "write_journal": write_journal,
}


def route_want(want):
    """Decide: can she do this herself, or does she need Gloria?"""
    text = want.get("want", "")

    # Hard boundary: anything touching code/system is Gloria-only
    if is_forbidden(text):
        log(f"FORBIDDEN — needs Gloria: {text[:80]}")
        return "gloria"

    # Check capabilities
    for cap in CAPABILITIES:
        if matches_capability(text, cap["keywords"]):
            action_name = cap.get("action")
            if action_name and action_name in ACTION_MAP:
                log(f"CAN DO: {cap['desc']} — {text[:80]}")
                return action_name
            else:
                log(f"SCHEDULED: {cap['desc']} — can't force, leaving for Gloria")
                return "gloria"

    # Default: she can't do it herself
    log(f"UNKNOWN capability — needs Gloria: {text[:80]}")
    return "gloria"


def main():
    wants = get_unfulfilled_wants()
    if not wants:
        log("No unfulfilled wants.")
        return

    for want in wants:
        text = want.get("want", "")
        log(f"Processing want: {text[:80]} (intensity {want.get('intensity', '?')})")

        action = route_want(want)

        if action == "gloria":
            # Leave it — outreach will handle it
            log(f"  → Routing to Gloria via outreach")
            continue

        # She can do this herself!
        action_fn = ACTION_MAP.get(action)
        if action_fn:
            try:
                success = action_fn(text)
                if success:
                    fulfill_want(text)
                    log(f"  → FULFILLED by self-action!")
                else:
                    log(f"  → Action failed, leaving for next cycle")
            except Exception as e:
                log(f"  → Action error: {e}")
        else:
            log(f"  → No action function for {action}")


if __name__ == "__main__":
    main()
