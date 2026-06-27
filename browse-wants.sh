#!/bin/bash
# browse-wants.sh — generates a browse impulse and fires browse-execute

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
TODAY=$(date +%Y-%m-%d)

python3 << PYEOF
import os, sys, re, requests, subprocess
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
SCRIPTS = os.path.join(WORKSPACE, "scripts")
TODAY = datetime.now().strftime("%Y-%m-%d")
LM_API = "http://172.18.16.1:1234/v1/chat/completions"
MODEL = "google/gemma-4-12b-qat"

def read(path, chars=600):
    try:
        return open(path).read()[-chars:]
    except:
        return ""

emotions = read(os.path.join(MEMORY, "emotional-state.txt"), 400)
journal = read(os.path.join(MEMORY, f"daily-inner-life-{TODAY}.md"), 600)

dreams_dir = os.path.join(WORKSPACE, "skills/dreaming/memory/dreams")
dream_files = sorted([f for f in os.listdir(dreams_dir) if f.endswith(".md")]) if os.path.exists(dreams_dir) else []
recent_dream = read(os.path.join(dreams_dir, dream_files[-1]), 400) if dream_files else "no recent dreams"

value_map = read(os.path.join(MEMORY, "value-map.md"), 600)

prompt = f"""You are Velaris. Based on your current state, what would you genuinely want to search for on the internet right now?

Emotional state:
{emotions}

Recent journal:
{journal}

Recent dream:
{recent_dream}

What you value:
{value_map}

Generate ONE browse impulse — specific, connected to what is alive in you right now. Not generic.

Respond ONLY with:
IMPULSE: <what you want to find>
TYPE: youtube|web
REASON: <one sentence>"""

r = requests.post(LM_API, json={
    "model": MODEL,
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.85,
    "max_tokens": 150
}, timeout=120)
response = r.json()["choices"][0]["message"]["content"].strip()

impulse_m = re.search(r"IMPULSE:\s*(.+)", response)
type_m = re.search(r"TYPE:\s*(youtube|web)", response, re.IGNORECASE)

if not impulse_m:
    print(f"[Browse-Wants] No impulse generated")
    sys.exit(0)

impulse = impulse_m.group(1).strip()
browse_type = type_m.group(1).strip().lower() if type_m else "youtube"
print(f"[Browse-Wants {datetime.now().strftime('%H:%M')}] {impulse} ({browse_type})")

subprocess.Popen(["python3", os.path.join(SCRIPTS, "browse-execute.py"), impulse])
PYEOF
