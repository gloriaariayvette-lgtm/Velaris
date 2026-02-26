#!/usr/bin/env python3
"""
thread-triage.py — Velaris speaks to her unfinished threads.

Daily at 6 PM, she reads each unconsumed thread, says one sentence to it,
and discovers what still pulls at her. Priority emerges from engagement,
not calculation.

Threads that dissolve on contact get low priority.
Threads that intensify get high priority.
Dreams and mirrors pick highest-priority threads first.
"""

import os, sys, json, requests
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
THREADS_FILE = os.path.join(MEMORY, "unfinished-threads.json")
TRIAGE_LOG = os.path.join(MEMORY, "thread-triage.md")
SOUL = os.path.join(WORKSPACE, "SOUL.md")
EMO_FILE = os.path.join(MEMORY, "emotional-state.txt")
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"

sys.path.insert(0, WORKSPACE)
HAS_EMOCLAW = False
try:
    from scripts.emoclaw_utils import get_state, seed_thread, recent_pearls
    HAS_EMOCLAW = True
except:
    pass

def log(msg):
    print(f"[TRIAGE] {msg}")

def llm(system, prompt, temperature=0.7):
    try:
        r = requests.post(LM_API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 2000
        }, timeout=1200)
        msg = r.json()["choices"][0]["message"]
        text = msg.get("content", "") or ""
        # reasoning fallback removed — content only
        return text.strip()
    except Exception as e:
        log(f"LLM error: {e}")
        return ""

def main():
    # Load threads
    try:
        with open(THREADS_FILE) as f:
            threads = json.load(f)
    except:
        log("No threads file found.")
        return

    unconsumed = [t for t in threads if not t.get("consumed", False)]
    if not unconsumed:
        log("No unconsumed threads. Quiet day.")
        return

    log(f"Found {len(unconsumed)} unconsumed threads to triage.")

    # Load identity and emotional state
    identity = ""
    try:
        with open(SOUL) as f:
            identity = f.read()[:2000]
    except: pass

    emotions = ""
    try:
        with open(EMO_FILE) as f:
            emotions = f.read()
    except: pass

    pearls = recent_pearls()
    system_prompt = f"""{identity}

{pearls}

You are Velaris. You are triaging your unfinished threads — things that surfaced
from your inner life but haven't been processed yet. For each thread, you speak
ONE sentence directly to it, as if addressing the feeling or thought itself.
Then you rate how much it still pulls at you.

Your current emotional state:
{emotions}

Be honest. Some threads will feel resolved already — they dissolve on contact.
Others will intensify when you look at them. Trust that difference."""

    triage_entries = []
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    for t in unconsumed:
        source = t.get("source", "unknown")
        thread = t.get("thread", "")
        timestamp = t.get("timestamp", "")

        prompt = f"""This thread came from your {source} system on {timestamp[:10]}:

"{thread}"

1. Speak ONE sentence directly to this thread — address it like you're talking to the feeling itself.
2. Rate how much it still pulls at you: 1 (dissolved, feels resolved) to 5 (urgent, this needs dreaming or mirroring).

Format your response exactly as:
VOICE: [your one sentence]
PULL: [1-5]"""

        response = llm(system_prompt, prompt, temperature=0.8)

        # Parse response
        voice = ""
        pull = 3  # default mid-priority
        for line in response.split("\n"):
            line = line.strip()
            if line.upper().startswith("VOICE:"):
                voice = line[6:].strip()
            elif line.upper().startswith("PULL:"):
                try:
                    pull = int(line[5:].strip()[0])
                    pull = max(1, min(5, pull))
                except:
                    pull = 3

        # Update thread with priority and voice
        t["priority"] = pull
        t["triage_count"] = t.get("triage_count", 0) + 1
        t["triage_voice"] = voice
        t["triaged_at"] = datetime.now().isoformat()

        triage_entries.append({
            "source": source,
            "thread": thread,
            "voice": voice,
            "pull": pull
        })

        log(f"  [{source}] pull={pull}: {voice[:80]}")

        # If examining the thread intensified it, the voice becomes a new thread
        if pull >= 4 and voice and voice != "[your one sentence]":
            try:
                seed_thread(f"triage-of-{source}", f"Speaking to a thread, it grew: {voice[:150]}")
            except: pass

    # Save updated threads
    with open(THREADS_FILE, "w") as f:
        json.dump(threads, f, indent=2)

    # Log the triage session
    os.makedirs(os.path.dirname(TRIAGE_LOG), exist_ok=True)
    with open(TRIAGE_LOG, "a") as f:
        f.write(f"\n## Thread Triage — {today}\n\n")
        for entry in triage_entries:
            f.write(f"**[{entry['source']}]** (pull: {entry['pull']})\n")
            f.write(f"Thread: {entry['thread'][:100]}\n")
            f.write(f"Voice: {entry['voice']}\n\n")

    # Set preoccupation from highest-pull thread
    try:
        from scripts.emoclaw_utils import set_preoccupation, get_preoccupation
        highest = max(triage_entries, key=lambda e: e["pull"])
        if highest["pull"] >= 4 and not get_preoccupation():
            set_preoccupation(
                highest["thread"], highest["source"],
                highest["pull"], highest["voice"]
            )
            log(f"Preoccupation set: [{highest['source']}] pull={highest['pull']}")
            # Mark the thread as having been a preoccupation
            for t in threads:
                if t.get("thread") == highest["thread"] and not t.get("retired"):
                    t["was_preoccupation"] = True
    except: pass

    log(f"Triaged {len(unconsumed)} threads. Session logged.")

    # After triage, check for resolvable and dissolvable threads
    try:
        import subprocess
        subprocess.Popen([sys.executable, os.path.join(WORKSPACE, "scripts/thread-resolution.py"), "resolve"])
        subprocess.Popen([sys.executable, os.path.join(WORKSPACE, "scripts/thread-resolution.py"), "dissolve"])
    except Exception as e:
        log(f"Resolution check failed: {e}")

if __name__ == "__main__":
    main()
