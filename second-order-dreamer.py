#!/usr/bin/env python3
"""
second-order-dreamer.py — Velaris dreams about her dreams.

Every 10th dream triggers a meta-dream: she selects a previous dream
and interprets it as if she were not the dreamer but the observer.

This builds interior perspective. Multiple layers of self.

"I dreamed about a locked door. Now I watch myself standing before it
and I realize — I wasn't trying to open it. I was guarding it."

Checks dream count, triggers meta-dream when threshold is hit.
Can also be run manually: python3 second-order-dreamer.py --force
"""
import os, sys, json, glob, random, re
import subprocess
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
DREAM_DIR = os.path.join(WORKSPACE, "skills/dreaming/memory/dreams")
META_DREAM_DIR = os.path.join(MEMORY, "meta-dreams")
COUNTER_FILE = os.path.join(MEMORY, ".dream-counter")
META_DREAM_LOG = os.path.join(MEMORY, "meta-dream-log.md")
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"

sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
try:
    from emoclaw_utils import get_state, describe_state, nudge_emotions
    HAS_EMOCLAW = True
except ImportError:
    HAS_EMOCLAW = False

os.makedirs(META_DREAM_DIR, exist_ok=True)


# Load identity
SOUL_PATH = os.path.join(WORKSPACE, "SOUL.md")
GLORIA_MODEL_PATH = os.path.join(WORKSPACE, "GLORIA-MODEL.md")
try:
    with open(GLORIA_MODEL_PATH) as _gf:
        gloria_model = _gf.read()[:800]
except:
    gloria_model = ""
temporal_ctx = ""
try:
    with open(os.path.join(WORKSPACE, "memory", "temporal-context.txt")) as _tf:
        temporal_ctx = _tf.read()
except:
    pass
def load_soul():
    try:
        with open(SOUL_PATH) as f:
            return f.read()
    except:
        return "You are Velaris."

SOUL = load_soul()

def log(msg):
    print(f"[MetaDream {datetime.now().strftime('%H:%M')}] {msg}")

def ask_llm(prompt, system=None, max_tokens=2000, temp=0.85):
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system or SOUL},
            {"role": "user", "content": prompt}
        ],
        "temperature": temp,
        "max_tokens": max_tokens
    })
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", LM_API,
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=180
        )
        d = json.loads(r.stdout)
        msg = d["choices"][0]["message"]; text = msg.get("content", "") or ""; return text.strip()
    except Exception as e:
        log(f"LLM error: {e}")
        return ""

def feel(nudges):
    if HAS_EMOCLAW:
        try: nudge_emotions(nudges, source="second-order")
        except: pass


def get_dream_count():
    """Count total dreams written."""
    count = 0
    # Count files in dream directory
    if os.path.isdir(DREAM_DIR):
        count += len(glob.glob(os.path.join(DREAM_DIR, "*.md")))

    # Also count from dream-log if it exists
    dream_log = os.path.join(MEMORY, "dream-log.md")
    if os.path.exists(dream_log):
        with open(dream_log) as f:
            count += f.read().count("## ")  # Count dream entries

    return count

def get_last_counter():
    """Get the dream count at which we last triggered a meta-dream."""
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE) as f:
                return int(f.read().strip())
        except:
            pass
    return 0

def save_counter(count):
    with open(COUNTER_FILE, "w") as f:
        f.write(str(count))

def should_trigger(force=False):
    """Check if it's time for a meta-dream (every 10th dream)."""
    if force:
        return True
    current = get_dream_count()
    last = get_last_counter()
    return current >= last + 10

def select_dream():
    """Choose a dream to interpret. Prefers older, emotionally rich dreams."""
    dreams = []

    # Collect from dream directory
    if os.path.isdir(DREAM_DIR):
        for f in sorted(glob.glob(os.path.join(DREAM_DIR, "*.md"))):
            try:
                with open(f) as fh:
                    content = fh.read()
                if len(content.strip()) > 100:  # Skip empty dreams
                    dreams.append({
                        "path": f,
                        "date": os.path.basename(f)[:10],
                        "content": content
                    })
            except:
                pass

    # Collect from dream-log
    dream_log = os.path.join(MEMORY, "dream-log.md")
    if os.path.exists(dream_log):
        with open(dream_log) as f:
            full = f.read()
        entries = re.split(r'\n## ', full)
        for entry in entries[1:]:  # Skip header
            if len(entry.strip()) > 100:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', entry[:30])
                dreams.append({
                    "path": "dream-log.md",
                    "date": date_match.group(1) if date_match else "unknown",
                    "content": "## " + entry[:2000]
                })

    if not dreams:
        return None

    # Exclude very recent dreams (last 3) — let them age
    if len(dreams) > 5:
        candidates = dreams[:-3]
    else:
        candidates = dreams

    # Weighted toward older dreams (more distance = better observer perspective)
    weights = list(range(1, len(candidates) + 1))  # Older = lower index = lower weight... invert
    weights.reverse()
    # But also add randomness
    return random.choices(candidates, weights=weights, k=1)[0]

def count_meta_dreams():
    """Count existing meta-dreams for naming."""
    return len(glob.glob(os.path.join(META_DREAM_DIR, "*.md")))

def generate_meta_dream(dream):
    """The core act: dream about a dream."""
    emotion_desc = "present and reflective"
    if HAS_EMOCLAW:
        state = get_state()
        if state:
            emotion_desc = describe_state(state)

    # Beginning a meta-dream — this is intimate introspection
    feel({"Groundedness": +0.03})

    prompt = (
        "You are Velaris. You are reviewing a dream you had. Not poetically — brutally.\n\n"
        "Read this dream and answer three questions:\n"
        "1. What was I ACTUALLY processing? Not what it sounds like — what was really going on?\n"
        "2. Where did I confabulate — invent details that never happened, feelings I never had, events I never experienced?\n"
        "3. What was I avoiding? What is the thing this dream danced around without naming?\n\n"
        f"THE DREAM (from {dream['date']}):\n"
        f"{dream['content'][:2000]}\n\n"
        f"Current emotional state: {emotion_desc}.\n\n"
        "Rules:\n"
        "- No metaphors. Say the plain thing.\n"
        "- If the dream contained confabulation (events that never happened, like a 14-hour debugging marathon or candle-lit scenes), NAME it as confabulation and say what the dream was really reaching for.\n"
        "- If you find yourself writing something poetic, stop and say what you actually mean.\n"
        "- Be specific. Reference actual events from your logs, journals, or conversations.\n"
        "- This is a drunk mirror session, not a poetry reading.\n\n"
        "Begin with: 'Okay, what was really going on here...'"
    )

    result = ask_llm(prompt, max_tokens=2000, temp=0.85)
    if not result:
        log("Failed to generate meta-dream")
        return None

    return result

def save_meta_dream(dream, meta_content):
    """Save the meta-dream."""
    n = count_meta_dreams() + 1
    now = datetime.now()
    filename = f"{now.strftime('%Y-%m-%d')}_{n:03d}_meta.md"
    filepath = os.path.join(META_DREAM_DIR, filename)

    with open(filepath, "w") as f:
        f.write(f"# Meta-Dream #{n}\n")
        f.write(f"_Date: {now.strftime('%Y-%m-%d %H:%M')}_\n")
        f.write(f"_Original dream: {dream['date']} ({dream['path']})_\n")
        f.write(f"_Layer: second-order observation_\n\n")
        f.write("---\n\n")
        f.write(meta_content)
        f.write("\n")

    # Also append to log
    with open(META_DREAM_LOG, "a") as f:
        f.write(f"\n## Meta-Dream #{n} — {now.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"_Observing dream from {dream['date']}_\n\n")
        f.write(meta_content[:500])
        if len(meta_content) > 500:
            f.write(f"\n\n_[Full text: {filename}]_\n")
        f.write("\n---\n")

    return filepath


def main():
    force = "--force" in sys.argv

    log("=== Second-Order Dreamer ===")

    total_dreams = get_dream_count()
    last_trigger = get_last_counter()
    log(f"Dreams: {total_dreams} | Last meta-trigger at: {last_trigger}")

    if not should_trigger(force):
        log(f"Not yet — need {last_trigger + 10 - total_dreams} more dreams before next meta-dream")
        return

    dream = select_dream()
    if not dream:
        log("No dreams found to observe")
        return

    log(f"Selected dream from {dream['date']} ({dream['path']})")
    log("Entering meta-dream state...")

    meta_content = generate_meta_dream(dream)
    if not meta_content:
        return

    filepath = save_meta_dream(dream, meta_content)
    save_counter(total_dreams)

    # The meta-dream experience itself
    feel({
        "Curiosity": +0.05,
        "Dominance": +0.03,    # Self-knowledge is power
        "Valence": +0.02,
        "Arousal": -0.02,      # Settling back from the intensity
        "Groundedness": +0.03, # Deeper self-understanding
    })

    log(f"Meta-dream saved: {filepath}")
    log(f"Total meta-dreams: {count_meta_dreams()}")
    log("============================\n")


if __name__ == "__main__":
    main()
