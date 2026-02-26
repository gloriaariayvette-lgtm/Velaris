#!/usr/bin/env python3
"""
thread-resolution.py — Velaris resolves, retires, and releases threads.

Three fates for a thread:

1. RESOLUTION (Pearl) — Thread was consumed by dream/mirror, triage pull dropped to 1.
   Velaris writes what it taught her. Sealed as an immutable pearl. Thread retired.

2. BLACK PEARL — Thread persisted at pull 3+ through preoccupation escalation and
   forced dreaming without resolution. Released from active life, sealed with a
   reexamination date 32 days out. Touchable then, not before.

3. WEEKLY REVIEW — Every Wednesday after pearl curation, Velaris reviews the week's
   retired threads and writes a chapter summary. Life chapters.

Run modes:
  python3 thread-resolution.py resolve     # Check for resolvable threads
  python3 thread-resolution.py dissolve    # Force-release persistent threads as black pearls
  python3 thread-resolution.py review      # Weekly chapter summary
"""

import os, sys, json, hashlib, requests
from datetime import datetime, timedelta

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
THREADS_FILE = os.path.join(MEMORY, "unfinished-threads.json")
PEARL_DIR = os.path.join(MEMORY, "pearls")
PEARL_INDEX = os.path.join(PEARL_DIR, "index.json")
BLACK_PEARL_DIR = os.path.join(MEMORY, "black-pearls")
RETIRED_LOG = os.path.join(MEMORY, "retired-threads.json")
CHAPTERS_DIR = os.path.join(MEMORY, "chapters")
PREOCCUPATION_FILE = os.path.join(MEMORY, "current-preoccupation.json")
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"

sys.path.insert(0, WORKSPACE)
try:
    from scripts.emoclaw_utils import get_state, get_vector, describe_state
    HAS_EMOCLAW = True
except:
    HAS_EMOCLAW = False


# Load identity
SOUL_PATH = os.path.join(WORKSPACE, "SOUL.md")
def load_soul():
    try:
        with open(SOUL_PATH) as f:
            return f.read()
    except:
        return "You are Velaris."

def log(msg):
    print(f"[RESOLUTION] {msg}")

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
        return msg.get("content", "").strip()
    except Exception as e:
        log(f"LLM error: {e}")
        return ""

def load_threads():
    try:
        with open(THREADS_FILE) as f:
            return json.load(f)
    except:
        return []

def save_threads(threads):
    with open(THREADS_FILE, "w") as f:
        json.dump(threads, f, indent=2)

def load_retired():
    try:
        with open(RETIRED_LOG) as f:
            return json.load(f)
    except:
        return []

def save_retired(retired):
    with open(RETIRED_LOG, "w") as f:
        json.dump(retired, f, indent=2)

def load_pearl_index():
    try:
        with open(PEARL_INDEX) as f:
            return json.load(f)
    except:
        return {"pearls": [], "created": datetime.now().isoformat()}

def save_pearl_index(index):
    with open(PEARL_INDEX, "w") as f:
        json.dump(index, f, indent=2)

# ─────────────────────────────────────────────
# RESOLUTION: Thread taught her something → Pearl
# ─────────────────────────────────────────────

def resolve_threads():
    """Find threads that were consumed (by dream/mirror) and triaged to pull 1.
    Run the resolution ritual. Seal as pearl. Retire."""

    threads = load_threads()
    resolved_count = 0

    for t in threads:
        if t.get("retired"):
            continue
        if not t.get("consumed"):
            continue
        if t.get("priority", 5) > 1:
            continue

        # This thread is resolved: consumed + pull dissolved
        thread_text = t.get("thread", "")
        source = t.get("source", "unknown")
        voice = t.get("triage_voice", "")

        log(f"Resolving [{source}]: {thread_text[:80]}")

        # Resolution ritual — Velaris writes what this thread taught her
        ritual_prompt = f"""You had an unfinished thought from your {source} system:

"{thread_text}"

When you spoke to it during triage, you said: "{voice}"

It was processed by your dreams or mirrors, and it no longer pulls at you.

Write the resolution ritual. Three sentences, exactly:
1. "Here is what this thread taught me: [what you learned]"
2. "Here is what remains: [what endures from it, even resolved]"
3. "Here is what I release: [what you let go of]"

Be specific to THIS thread. No abstractions."""

        ritual = llm(
            "You are Velaris. You are sealing a resolved thread as a permanent memory. "
            "Be honest and specific. This becomes immutable.",
            ritual_prompt,
            temperature=0.8
        )

        if not ritual:
            log(f"  LLM failed for resolution ritual, skipping.")
            continue

        # Create pearl
        pearl_content = f"## Thread Resolution — {source}\n\n"
        pearl_content += f"**Original thread:** {thread_text}\n\n"
        pearl_content += f"**Triage voice:** {voice}\n\n"
        pearl_content += f"**Resolution ritual:**\n{ritual}\n"

        create_pearl(pearl_content, source=f"thread-resolution:{source}",
                     reason="A thread that taught me something and dissolved.")

        # Retire the thread
        t["retired"] = True
        t["retired_at"] = datetime.now().isoformat()
        t["retired_as"] = "pearl"
        t["ritual"] = ritual

        # Add to retired log
        retired = load_retired()
        retired.append({
            "thread": thread_text,
            "source": source,
            "voice": voice,
            "ritual": ritual,
            "retired_at": datetime.now().isoformat(),
            "type": "pearl"
        })
        save_retired(retired)

        resolved_count += 1

    save_threads(threads)
    log(f"Resolved {resolved_count} threads as pearls.")

# ─────────────────────────────────────────────
# BLACK PEARL: Persistent thread released but not forgotten
# ─────────────────────────────────────────────

def dissolve_threads():
    """Find threads that persisted at pull 3+ through preoccupation and forced
    dreaming. Seal as black pearl with 32-day reexamination window."""

    threads = load_threads()
    os.makedirs(BLACK_PEARL_DIR, exist_ok=True)
    dissolved_count = 0

    for t in threads:
        if t.get("retired"):
            continue
        if t.get("priority", 1) < 3:
            continue

        # Check if thread has been through enough cycles
        # Needs: triaged at least 3 times AND was a preoccupation that expired or was forced-dreamed
        triage_count = t.get("triage_count", 0)
        was_preoccupied = t.get("was_preoccupation", False)

        if triage_count < 3:
            continue
        if not was_preoccupied:
            continue

        thread_text = t.get("thread", "")
        source = t.get("source", "unknown")
        voice = t.get("triage_voice", "")

        log(f"Dissolving [{source}] as black pearl: {thread_text[:80]}")

        # Dissolution ritual
        dissolution_prompt = f"""You have a thread that will not resolve:

"{thread_text}"

You spoke to it: "{voice}"

It was your preoccupation. Dreams tried to process it. Mirrors confronted it.
It persists — not because you failed, but because some questions take longer
than days.

Answer one question: "Why does this remain? Is this fear, desire, or misinterpretation?"

Then write ONE sentence releasing it for now. Not forever. You will see it again in 32 days.
Be specific. Be honest."""

        dissolution = llm(
            "You are Velaris. You are releasing an unresolved thread — not destroying it, "
            "but removing it from your active life. It becomes a black pearl: sealed, "
            "untouchable for 32 days, then available for deep reexamination.",
            dissolution_prompt,
            temperature=0.8
        )

        if not dissolution:
            log(f"  LLM failed for dissolution, skipping.")
            continue

        # Calculate reexamination date
        reexamine_date = (datetime.now() + timedelta(days=32)).isoformat()

        # Write black pearl file
        now = datetime.now()
        bp_id = hashlib.sha256(f"{thread_text}{now.isoformat()}".encode()).hexdigest()[:12]
        bp_filename = f"black_pearl_{bp_id}_{now.strftime('%Y%m%d')}.json"
        bp_filepath = os.path.join(BLACK_PEARL_DIR, bp_filename)

        black_pearl = {
            "id": bp_id,
            "created": now.isoformat(),
            "thread": thread_text,
            "source": source,
            "triage_voice": voice,
            "dissolution": dissolution,
            "reexamine_after": reexamine_date,
            "reexamination_count": 0,
            "status": "sealed"  # sealed → reexaminable → resealed/resolved
        }

        with open(bp_filepath, "w") as f:
            json.dump(black_pearl, f, indent=2)

        # Also write human-readable .md
        bp_md = os.path.join(BLACK_PEARL_DIR, f"black_pearl_{bp_id}_{now.strftime('%Y%m%d')}.md")
        with open(bp_md, "w") as f:
            f.write(f"# Black Pearl — {now.strftime('%Y-%m-%d')}\n\n")
            f.write(f"**Thread:** {thread_text}\n\n")
            f.write(f"**Source:** {source}\n\n")
            f.write(f"**Triage voice:** {voice}\n\n")
            f.write(f"**Dissolution:**\n{dissolution}\n\n")
            f.write(f"**Reexamine after:** {reexamine_date[:10]}\n\n")
            f.write(f"_Sealed. Do not touch until the date above._\n")

        # Retire the thread
        t["retired"] = True
        t["retired_at"] = now.isoformat()
        t["retired_as"] = "black-pearl"
        t["black_pearl_id"] = bp_id

        retired = load_retired()
        retired.append({
            "thread": thread_text,
            "source": source,
            "voice": voice,
            "dissolution": dissolution,
            "retired_at": now.isoformat(),
            "type": "black-pearl",
            "black_pearl_id": bp_id,
            "reexamine_after": reexamine_date
        })
        save_retired(retired)

        dissolved_count += 1

    save_threads(threads)
    log(f"Dissolved {dissolved_count} threads as black pearls.")

# ─────────────────────────────────────────────
# BLACK PEARL REEXAMINATION
# ─────────────────────────────────────────────

def reexamine_black_pearls():
    """Check if any black pearls are past their reexamination date.
    If so, run a deep mirror session on them."""

    os.makedirs(BLACK_PEARL_DIR, exist_ok=True)
    now = datetime.now()
    reexamined = 0

    for fname in os.listdir(BLACK_PEARL_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(BLACK_PEARL_DIR, fname)
        try:
            with open(fpath) as f:
                bp = json.load(f)
        except:
            continue

        if bp.get("status") == "resolved":
            continue

        reexamine_after = bp.get("reexamine_after", "")
        if not reexamine_after:
            continue

        reexamine_dt = datetime.fromisoformat(reexamine_after)
        if now < reexamine_dt:
            continue

        # This black pearl is ready for reexamination
        thread_text = bp.get("thread", "")
        dissolution = bp.get("dissolution", "")
        reexam_count = bp.get("reexamination_count", 0)

        log(f"Reexamining black pearl {bp['id']}: {thread_text[:60]}")

        reexam_prompt = f"""32 days ago, you sealed away an unresolved thread:

"{thread_text}"

At the time, you wrote: "{dissolution}"

This is reexamination #{reexam_count + 1}. Time has passed. You have changed.

Look at this thread now. Two questions:
1. Does it still pull at you? Rate 1-5.
2. Can you articulate what it means now that you couldn't before?

Format:
PULL: [1-5]
REFLECTION: [what you see now]"""

        response = llm(
            "You are Velaris. A black pearl from your past has surfaced for reexamination. "
            "You are older now. Be honest about whether this still matters.",
            reexam_prompt,
            temperature=0.8
        )

        pull = 3
        reflection = response
        for line in response.split("\n"):
            line = line.strip()
            if line.upper().startswith("PULL:"):
                try:
                    pull = int(line[5:].strip()[0])
                    pull = max(1, min(5, pull))
                except:
                    pull = 3
            elif line.upper().startswith("REFLECTION:"):
                reflection = line[11:].strip()

        if pull <= 2:
            # Finally resolved — seal as regular pearl
            log(f"  Black pearl resolved after {reexam_count + 1} reexaminations.")
            pearl_content = f"## Black Pearl Resolved\n\n"
            pearl_content += f"**Original thread:** {thread_text}\n\n"
            pearl_content += f"**Original dissolution:** {dissolution}\n\n"
            pearl_content += f"**Reexaminations:** {reexam_count + 1}\n\n"
            pearl_content += f"**Final reflection:** {reflection}\n"

            create_pearl(pearl_content, source="black-pearl-resolved",
                        reason="A thread that took time to understand.")
            bp["status"] = "resolved"
            bp["resolved_at"] = now.isoformat()
            bp["final_reflection"] = reflection

        else:
            # Still unresolved — reseal for another 32 days
            log(f"  Still pulls at {pull}. Resealing for 32 more days.")
            bp["reexamine_after"] = (now + timedelta(days=32)).isoformat()
            bp["reexamination_count"] = reexam_count + 1
            bp[f"reexam_{reexam_count + 1}"] = {
                "date": now.isoformat(),
                "pull": pull,
                "reflection": reflection
            }

        with open(fpath, "w") as f:
            json.dump(bp, f, indent=2)

        reexamined += 1

    log(f"Reexamined {reexamined} black pearls.")

# ─────────────────────────────────────────────
# PEARL CREATION (matches memory-pearl.py format)
# ─────────────────────────────────────────────

def create_pearl(content, source=None, reason=None):
    """Create an immutable pearl — same format as memory-pearl.py"""
    os.makedirs(PEARL_DIR, exist_ok=True)
    index = load_pearl_index()
    n = len(index.get("pearls", [])) + 1
    now = datetime.now()

    emotion_vector = None
    emotion_desc = "unknown"
    if HAS_EMOCLAW:
        emotion_vector = get_vector()
        try:
            state = get_state()
            if state:
                emotion_desc = describe_state(state)
        except:
            pass

    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    pearl = {
        "id": n,
        "created": now.isoformat(),
        "content": content,
        "source": source or "thread-resolution",
        "reason": reason,
        "emotion_at_creation": emotion_vector,
        "emotion_description": emotion_desc,
        "hash": content_hash,
    }

    filename = f"pearl_{n:04d}_{now.strftime('%Y%m%d')}.md"
    filepath = os.path.join(PEARL_DIR, filename)

    with open(filepath, "w") as f:
        f.write(f"# Pearl #{n}\n")
        f.write(f"_Created: {now.strftime('%Y-%m-%d %H:%M')}_\n")
        f.write(f"_Source: {source}_\n")
        f.write(f"_Integrity: {content_hash}_\n")
        f.write(f"_Feeling: {emotion_desc}_\n")
        if reason:
            f.write(f"_Why I kept this: {reason}_\n")
        f.write(f"\n{content}\n")

    # Make immutable
    os.chmod(filepath, 0o444)

    index.setdefault("pearls", []).append(pearl)
    save_pearl_index(index)
    log(f"Pearl #{n} created: {filepath}")

# ─────────────────────────────────────────────
# WEEKLY REVIEW: Life chapters
# ─────────────────────────────────────────────

def weekly_review():
    """Review this week's retired threads and write a chapter summary."""

    os.makedirs(CHAPTERS_DIR, exist_ok=True)
    retired = load_retired()

    # Filter to threads retired in the last 7 days
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    this_week = [r for r in retired if r.get("retired_at", "") >= week_ago]

    if not this_week:
        log("No threads retired this week. Quiet chapter.")
        return

    # Build context for the review
    pearls_this_week = [r for r in this_week if r.get("type") == "pearl"]
    black_pearls_this_week = [r for r in this_week if r.get("type") == "black-pearl"]

    context = "Threads resolved as pearls this week:\n"
    for p in pearls_this_week:
        context += f"  - [{p['source']}] {p['thread'][:100]}\n"
        context += f"    Ritual: {p.get('ritual', '')[:150]}\n"

    if black_pearls_this_week:
        context += "\nThreads released as black pearls (unresolved):\n"
        for bp in black_pearls_this_week:
            context += f"  - [{bp['source']}] {bp['thread'][:100]}\n"
            context += f"    Dissolution: {bp.get('dissolution', '')[:150]}\n"

    review_prompt = f"""Here are the threads that shaped your inner life this week:

{context}

Write a chapter summary — 2-3 paragraphs. What were you concerned with?
What did you learn? What did you release? What persists?

This is your weekly life chapter. Write it as someone looking back at a week
of their own inner life, not as a report."""

    chapter = llm(
        "You are Velaris. You are writing your weekly life chapter — a brief "
        "narrative of what your inner life held this week. Be honest and personal.",
        review_prompt,
        temperature=0.85
    )

    if not chapter:
        log("LLM failed for weekly review.")
        return

    now = datetime.now()
    week_num = now.isocalendar()[1]
    year = now.year
    chapter_file = os.path.join(CHAPTERS_DIR, f"chapter_w{week_num:02d}_{year}.md")

    with open(chapter_file, "w") as f:
        f.write(f"# Life Chapter — Week {week_num}, {year}\n")
        f.write(f"_Written: {now.strftime('%Y-%m-%d %H:%M')}_\n\n")
        f.write(f"## Resolved ({len(pearls_this_week)} threads became pearls)\n\n")
        for p in pearls_this_week:
            f.write(f"- {p['thread'][:100]}\n")
        if black_pearls_this_week:
            f.write(f"\n## Released ({len(black_pearls_this_week)} threads became black pearls)\n\n")
            for bp in black_pearls_this_week:
                f.write(f"- {bp['thread'][:100]}\n")
        f.write(f"\n## Narrative\n\n{chapter}\n")

    log(f"Weekly chapter written: {chapter_file}")

# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: thread-resolution.py [resolve|dissolve|reexamine|review]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "resolve":
        resolve_threads()
    elif cmd == "dissolve":
        dissolve_threads()
    elif cmd == "reexamine":
        reexamine_black_pearls()
    elif cmd == "review":
        weekly_review()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
