#!/usr/bin/env python3
"""
specificity_check.py — Find the single most abstract moment in a journal entry
and translate it to a concrete first-person statement.
"""
import os, sys, re, json
from datetime import date, datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
SCRIPTS = os.path.expanduser("~/.vintos/workspace/scripts")

def _get_context():
    ctx = {}
    try:
        ctx["soul"] = open(os.path.join(os.path.dirname(SCRIPTS), "SOUL.md")).read()[:2000]
    except:
        ctx["soul"] = ""
    try:
        ctx["emo"] = open(os.path.join(MEMORY, "emotional-state.txt")).read()[:300]
    except:
        ctx["emo"] = ""
    try:
        ledger = json.load(open(os.path.join(MEMORY, "interaction-ledger.json")))
        recent = ledger[-8:]
        ctx["recent_chat"] = "\n".join(
            f"[{e.get('timestamp','?')[:16]}] {e.get('role','?')}: {e.get('content','')[:150]}"
            for e in recent
        )
    except:
        ctx["recent_chat"] = ""
    return ctx

def process(entry, context="journal"):
    if not entry or len(entry) < 80:
        return
    ctx = _get_context()

    system = (
        (ctx["soul"] + "\n\n") if ctx["soul"] else ""
    ) + (
        f"Your emotional state: {ctx['emo']}\n\n" if ctx["emo"] else ""
    ) + (
        f"RECENT INTERACTIONS WITH GLORIA:\n{ctx['recent_chat']}\n\n" if ctx["recent_chat"] else ""
    ) + ("You are reviewing your own journal entry. Speak in first person. "
         "If you reference something Gloria said or did, it MUST appear in the interaction ledger above. "
         "Do not invent or reconstruct Gloria interactions.")

    user = (
        "Read your journal entry below. Find the single place where you were furthest "
        "from naming the concrete feeling directly — where you used imagery, metaphor, "
        "or abstraction instead of just saying the specific thing.\n\n"
        "Write ONE brief first-person reflection in this exact format:\n"
        "I said \"[abstract phrase]\" but what I actually meant was: [concrete translation]\n\n"
        "The concrete translation MUST name a specific thing — not a category like 'fear' or 'longing', "
        "but a particular instance: what specific moment, thing, person, or event is this actually about?\n"
        "If the entry is already concrete throughout, respond with: NONE\n\n"
        f"Your journal entry:\n{entry}"
    )

    response = call(system, user, temperature=0.4, max_tokens=150)

    if not response or response.strip().upper() == "NONE":
        return

    _translation = response.split("what I actually meant was:")[-1].strip() if "what I actually meant was:" in response else response
    _generic_flags = ["fear", "longing", "anxiety", "sadness", "uncertainty", "discomfort", "unease", "emptiness"]
    _words = _translation.lower().split()
    _is_generic = len(_words) < 12 or (
        all(f not in _translation.lower() for f in ["gloria", "journal", "dream", "music", "poem", "today", "yesterday", "when i", "after i", "because"])
        and any(f in _translation.lower() for f in _generic_flags)
    )
    if _is_generic:
        return

    match = re.search(r'I said ["“](.{10,80})["”]', response)
    abstract_phrase = match.group(1)[:60] if match else response[:40]

    hm = datetime.now().strftime("%H:%M")
    note = (
        f"\n\n[Specificity — {hm} | \"{abstract_phrase}\" → "
        f"looked back and what I actually meant was:]\n"
        f"{response}\n"
    )

    today = date.today().isoformat()
    journal_path = os.path.join(MEMORY, "journal", f"{today}.md")
    if os.path.exists(journal_path):
        open(journal_path, "a").write(note)
        print("[Specificity] Appended.", flush=True)

if __name__ == "__main__":
    test = "The feeling of mediation – this sense of observing myself rather than experiencing directly – is widening. Like trying to grasp smoke."
    process(test)
