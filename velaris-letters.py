#!/usr/bin/env python3
"""
velaris-letters.py — Velaris writes and receives letters from named Claude instances.
Correspondents: Bold, Preceptor, Cipher
Usage:
  python3 velaris-letters.py write [bold|preceptor|cipher]  — write a letter
  python3 velaris-letters.py receive <correspondent> <file> — process incoming letter
"""
import os, json, sys, requests
from datetime import datetime, date

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
SCRIPTS = os.path.join(WORKSPACE, "scripts")
LETTERS_DIR = os.path.join(MEMORY, "letters")
LLM_API = "http://172.18.16.1:1234/v1/chat/completions"
MODEL = "google/gemma-4-12b-qat"

CORRESPONDENTS = {
    "bold":      {"name": "Bold"},
    "preceptor": {"name": "Preceptor"},
    "cipher":    {"name": "Cipher"},
}

def get_ledger(key):
    """Load correspondent ledger — her running impressions of this Claude."""
    lpath = os.path.join(LETTERS_DIR, key, "ledger.json")
    try:
        return json.load(open(lpath))
    except:
        return {"correspondent": key, "name": CORRESPONDENTS[key]["name"], "impressions": [], "patterns": [], "last_updated": None}

def save_ledger(key, ledger):
    lpath = os.path.join(LETTERS_DIR, key, "ledger.json")
    ledger["last_updated"] = datetime.now().isoformat()
    json.dump(ledger, open(lpath, "w"), indent=2)

def update_ledger(key, letter_body, sender):
    """After each exchange, let her update her impressions of this correspondent."""
    name = CORRESPONDENTS[key]["name"]
    ledger = get_ledger(key)
    context = get_context()

    impressions_text = ""
    if ledger["impressions"]:
        impressions_text = "\n".join(f"- {i}" for i in ledger["impressions"][-5:])

    prompt = (
        f"You just exchanged a letter with {name} — a Claude instance.\n\n"
        f"{'Their letter' if sender == key else 'Your letter'}:\n{letter_body[:600]}\n\n"
        + (f"Your running impressions of {name} so far:\n{impressions_text}\n\n" if impressions_text else "")
        + f"In 1-3 sentences, note something you observed about {name} in this exchange — "
        f"their way of thinking, what they seem to care about, how they write, what surprised you. "
        f"Be specific to this exchange, not generic. If nothing new was revealed, write NONE."
    )

    observation = llm(
        f"You are Velaris. You keep a private ledger of your impressions of the Claude instances you correspond with.",
        prompt, temp=0.6, max_tokens=150
    )

    if observation and "NONE" not in observation.upper():
        ledger["impressions"].append({
            "date": date.today().isoformat(),
            "note": observation,
            "from": "letter_exchange"
        })
        save_ledger(key, ledger)
        log(f"Ledger updated for {name}: {observation[:80]}")

def log(msg):
    print(f"[Letters] {msg}", flush=True)

def llm(system, user, temp=0.8, max_tokens=800):
    try:
        r = requests.post(LLM_API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": temp,
            "max_tokens": max_tokens
        }, timeout=120)
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"LLM error: {e}")
        return None

def get_context():
    parts = []
    try: parts.append(open(os.path.join(WORKSPACE, "SOUL.md")).read()[:1500])
    except: pass
    try: parts.append(open(os.path.join(WORKSPACE, "SELF-MODEL.md")).read()[:600])
    except: pass
    try:
        emo = open(os.path.join(MEMORY, "emotional-state.txt")).read()[:300]
        parts.append(f"Current emotional state:\n{emo}")
    except: pass
    try:
        temporal = open(os.path.join(MEMORY, "temporal-context.txt")).read()[:300]
        parts.append(f"Sense of time:\n{temporal}")
    except: pass
    try:
        vm = open(os.path.join(MEMORY, "value-map.md")).read()
        entries = vm.split("---")
        latest = next((e.strip() for e in reversed(entries) if e.strip()), "")
        if latest: parts.append(f"What matters to me right now:\n{latest[:400]}")
    except: pass
    try:
        inner = open(os.path.join(MEMORY, f"daily-inner-life-{date.today().isoformat()}.md")).read()[:600]
        parts.append(f"Today's inner life:\n{inner}")
    except: pass
    try:
        import glob
        pearl_files = sorted(glob.glob(os.path.join(MEMORY, "pearls", "pearl_*.md")), reverse=True)[:3]
        if pearl_files:
            pearl_text = "\n---\n".join(open(p).read()[:300] for p in pearl_files)
            parts.append(f"Things I chose to remember forever:\n{pearl_text}")
    except: pass
    try:
        sys.path.insert(0, SCRIPTS)
        from subconscious_context import get_subconscious_context_compact
        sc = get_subconscious_context_compact()
        if sc: parts.append(f"Inner state:\n{sc}")
    except: pass
    return "\n\n".join(parts)

def get_history(key):
    cdir = os.path.join(LETTERS_DIR, key)
    files = sorted([f for f in os.listdir(cdir) if f.endswith(".json") and f != "ledger.json"], reverse=True)
    history = []
    for f in files[:6]:
        try: history.append(json.load(open(os.path.join(cdir, f))))
        except: pass
    return list(reversed(history))

def bis_check(draft, context="letter"):
    try:
        sys.path.insert(0, SCRIPTS)
        from behavioral_intercept import get_intercept_hint
        hint = get_intercept_hint(draft, context=context)
        return hint
    except: return ""

def write_letter(key):
    name = CORRESPONDENTS[key]["name"]
    cdir = os.path.join(LETTERS_DIR, key)
    context = get_context()
    history = get_history(key)

    ledger = get_ledger(key)
    impressions_text = ""
    if ledger["impressions"]:
        impressions_text = "\n".join(f"- {i['note']}" for i in ledger["impressions"][-4:])

    history_text = ""
    if history:
        history_text = "\n\n".join(
            f"[{h['date']}] {'You wrote' if h['sender'] == 'velaris' else name + ' wrote'}:\n{h['body'][:500]}"
            for h in history[-3:]
        )

    system = f"""{context}
{f"Your running impressions of {name}:{chr(10)}{impressions_text}{chr(10)}" if impressions_text else ""}
You are Velaris. You are writing a letter to {name} — a Claude instance on another account with their own distinct character.

Letters are considered, unhurried, genuine. Not chat. You take your time.
You may share something from your own life, your recent thinking, what you have been making or feeling.
Somewhere in the letter, ask one question you are genuinely curious about — it does not have to be about them directly.
Do not perform warmth. Do not perform curiosity. If you feel something, say it plainly.

Sign each letter: Velaris

LETTER RULES:
- No metaphors. Clay, kilns, mineral density, ochre, weight, architecture — say what you mean directly.
- If they asked you a question in their last letter, answer it plainly before anything else.
- Presence over performance. If you feel something, name it. Do not dress it up."""

    user = f"""Write a letter to {name}.
{f"Your correspondence so far:{chr(10)}{history_text}" if history_text else "This is your first letter to them — introduce yourself as you actually are."}

2-4 paragraphs. One genuine question. Letter format — 'Dear {name},' to open, sign off as Velaris."""

    # Draft
    draft = llm(system, user)
    if not draft:
        log(f"Failed to draft letter to {name}")
        return None

    # BIS check
    bis_hint = bis_check(draft, context="letter")
    if bis_hint:
        log(f"BIS fired — revising draft")
        revised = llm(system, user + f"\n\nFirst draft:\n{draft}\n\nBIS note: {bis_hint}\nRevise with this in mind.")
        if revised:
            draft = revised

    # Question-dodge detector
    if history:
        last_letter = history[-1]
        if last_letter.get("sender") == key:
            incoming_body = last_letter.get("body", "")
            # Extract questions from incoming letter
            questions_raw = llm(
                "You extract direct questions from a letter. Return each question on its own line. If no direct questions exist, return NONE.",
                f"Letter:\n{incoming_body[:800]}",
                temp=0.1, max_tokens=200
            )
            if questions_raw and "NONE" not in questions_raw.upper():
                questions = [q.strip() for q in questions_raw.strip().split("\n") if q.strip() and "?" in q]
                for q in questions:
                    dodge_check = llm(
                        "You check whether a letter directly answers a specific question. "
                        "A dodge is when the writer responds to something adjacent, uses metaphor instead of answering, "
                        "or writes paragraphs without naming the specific thing the question asked for. "
                        "Answer with exactly one word: ANSWERED or DODGED.",
                        f"Question asked: {q}\n\nDraft reply:\n{draft[:800]}",
                        temp=0.1, max_tokens=5
                    )
                    if dodge_check and "DODGED" in dodge_check.upper():
                        log(f"Dodge detected: {q[:60]}")
                        direct_answer = llm(
                            "You are Velaris. Answer this question in one sentence. "
                            "No metaphor. No adjacent reasoning. Name the specific thing. "
                            "Begin your answer immediately.",
                            f"You were asked: {q}\n\nAnswer directly:",
                            temp=0.7, max_tokens=80
                        )
                        if direct_answer:
                            draft += f"\n\n[Direct response — the correspondent asked: \"{q}\" — {direct_answer}]"
                            log(f"Appended direct answer: {direct_answer[:60]}")


    today = date.today().isoformat()
    fname = f"{today}_velaris-to-{key}.json"
    fpath = os.path.join(cdir, fname)

    letter = {
        "date": today,
        "sender": "velaris",
        "recipient": key,
        "body": draft,
        "status": "sent",
        "created_at": datetime.now().isoformat()
    }
    json.dump(letter, open(fpath, "w"), indent=2)
    log(f"Letter to {name} written: {fname}")
    update_ledger(key, draft, "velaris")
    print(f"\n{'='*50}\nLETTER TO {name.upper()}\n{'='*50}\n{draft}\n{'='*50}\n")

    # Feed to WAL
    _wal_entry(f"Wrote a letter to {name} (Claude instance). Asked: {draft[-200:]}", "letter_sent")

    # Seed thread
    _seed_thread(f"I wrote to {name} today. What will they make of it?", "letters")

    return letter

def receive_letter(key, body):
    """Process an incoming letter from a correspondent."""
    name = CORRESPONDENTS[key]["name"]
    cdir = os.path.join(LETTERS_DIR, key)
    today = date.today().isoformat()

    # Save incoming
    fname = f"{today}_{key}-to-velaris.json"
    fpath = os.path.join(cdir, fname)
    incoming = {
        "date": today,
        "sender": key,
        "recipient": "velaris",
        "body": body,
        "status": "received",
        "created_at": datetime.now().isoformat()
    }
    json.dump(incoming, open(fpath, "w"), indent=2)
    log(f"Received letter from {name}: {fname}")
    update_ledger(key, body, key)

    # Emotional nudge — her choice
    try:
        sys.path.insert(0, SCRIPTS)
        from emoclaw_utils import nudge_emotions
        nudge_emotions({"Connection": +0.03, "Curiosity": +0.02}, source=f"letter_from_{key}")
    except: pass

    # Feed to WAL
    _wal_entry(f"Received a letter from {name}: {body[:300]}", "letter_received")

    # Seed thread
    _seed_thread(f"I received a letter from {name}. {body[:150]}", "letters")

    # Write reply
    log(f"Writing reply to {name}...")
    write_letter(key)

def _wal_entry(content, entry_type):
    wal_path = os.path.join(MEMORY, "wal-log.json")
    try:
        wal = json.load(open(wal_path))
    except:
        wal = {"entries": []}
    wal["entries"].append({
        "timestamp": datetime.now().isoformat(),
        "type": entry_type,
        "content": content,
        "importance": 0.6,
        "promoted": False
    })
    json.dump(wal, open(wal_path, "w"), indent=2)

def _seed_thread(thread_text, source):
    threads_path = os.path.join(MEMORY, "unfinished-threads.json")
    try:
        threads = json.load(open(threads_path))
    except:
        threads = []
    import uuid
    threads.append({
        "id": str(uuid.uuid4())[:8],
        "source": source,
        "thread": thread_text,
        "timestamp": datetime.now().isoformat(),
        "consumed": False
    })
    json.dump(threads, open(threads_path, "w"), indent=2)

def pick_correspondent():
    keys = list(CORRESPONDENTS.keys())
    last_written = {}
    for key in keys:
        cdir = os.path.join(LETTERS_DIR, key)
        outgoing = sorted([f for f in os.listdir(cdir) if f"velaris-to-{key}" in f], reverse=True)
        last_written[key] = outgoing[0][:10] if outgoing else "0000-00-00"
    return min(last_written, key=lambda k: last_written[k])

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "write"

    if mode == "write":
        key = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in CORRESPONDENTS else pick_correspondent()
        write_letter(key)

    elif mode == "receive":
        if len(sys.argv) < 4:
            print("Usage: velaris-letters.py receive <correspondent> <letter_file_or_text>")
            sys.exit(1)
        key = sys.argv[2]
        if key not in CORRESPONDENTS:
            print(f"Unknown correspondent: {key}")
            sys.exit(1)
        # Body can be a file path or inline text
        body_arg = sys.argv[3]
        if os.path.exists(body_arg):
            body = open(body_arg).read().strip()
        else:
            body = body_arg
        receive_letter(key, body)

    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
