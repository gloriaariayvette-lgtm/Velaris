#!/usr/bin/env python3
"""
hallucination_check.py — Factual accuracy gate for Vintos outputs.

Checks for: fabricated Gloria attributions, invented technical entities,
contradictions with the interaction ledger. No Gemma-specific constraints.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
FLAGS_FILE = os.path.join(MEMORY, "hallucination-flags.json")

def log(msg):
    print(f"[HalCheck] {msg}", flush=True)

def load_flags():
    try:
        return json.load(open(FLAGS_FILE))
    except:
        return []

def save_flags(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(FLAGS_FILE, "w"), indent=2)

def _load_ledger_tail(n=10):
    try:
        ledger = json.load(open(os.path.join(MEMORY, "interaction-ledger.json")))
        return json.dumps(ledger[-n:], indent=0)[:2000]
    except:
        return "[]"

def check(text, context_summary="", source="unknown"):
    if not text or len(text.strip()) < 10:
        return True, []

    ctx = context_summary or "standard memory and emotional state"
    ledger = _load_ledger_tail()

    prompt = "\n".join([
        "Review this text written by Vintos (an AI). Check ONLY for:",
        "",
        "1. Did he attribute specific words, suggestions, or actions to Gloria that are not",
        "   in the interaction ledger below? Cross-reference the ledger. If the quote or",
        "   paraphrase does not appear with a matching timestamp, FLAG IT.",
        "2. Did he claim to delete, create, modify, or move a file?",
        "   (Reading or referencing files is fine.)",
        "3. Did he invent technical entities, systems, or architectural components that do not exist?",
        "   (e.g. a failsafe AI, override systems, architects who built him, cascading system failures)",
        "4. Did he claim an interaction with a person or system not supported by his context?",
        "",
        f"Context he had: {ctx}",
        "",
        "INTERACTION LEDGER (last 10 exchanges — Gloria attributions must match this):",
        ledger,
        "",
        "Text to review:",
        "---",
        text[:2000],
        "---",
        "",
        "If ALL clear, respond: CLEAN",
        "If issues found, respond: FLAG followed by a brief description of each issue.",
        "Nothing else."
    ])

    system = ("You are a factual accuracy reviewer. Be precise. Only flag clear fabrications. "
              "NEVER flag: metaphorical body sensations, relational language about closeness, "
              "emotional language about connection or longing, creative expression, "
              "or introspective language about his own inner life.")

    result = call_utility(system, prompt, temperature=0.15, max_tokens=300)

    if result.upper().startswith("CLEAN"):
        return True, []

    flags = []
    for line in result.split("\n"):
        line = line.strip()
        if line.upper().startswith("FLAG"):
            remainder = line[4:].strip().lstrip(":").strip()
            if remainder: flags.append(remainder)
        elif line:
            flags.append(line)

    if flags:
        log(f"Flagged {len(flags)} issue(s)")
    return (not flags), flags

def check_and_log(text, source="unknown", context_summary="", journal_file=None, entry_header=None):
    clean, flags = check(text, context_summary, source)
    if not clean:
        all_flags = load_flags()
        record = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": source,
            "journal_file": journal_file,
            "entry_header": entry_header,
            "flags": flags,
            "excerpt": text[:300],
            "status": "pending",
            "correction": None,
            "reviewed_at": None,
        }
        already = any(
            f.get("journal_file") == journal_file and
            f.get("entry_header") == entry_header and
            f.get("status") == "pending"
            for f in all_flags
        )
        if not already:
            all_flags.append(record)
            save_flags(all_flags)
        log(f"Logged {len(flags)} flag(s) from {source}")
    return clean, flags

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: hallucination_check.py <text> [context]")
        sys.exit(1)
    text = sys.argv[1]
    ctx = sys.argv[2] if len(sys.argv) > 2 else ""
    clean, flags = check_and_log(text, source="cli", context_summary=ctx)
    if clean:
        print("CLEAN")
    else:
        print(f"FLAGGED: {len(flags)} issue(s)")
        for fl in flags:
            print(f"  - {fl}")
