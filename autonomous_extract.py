#!/usr/bin/env python3
"""
autonomous_extract.py — Master extraction runner.
Pulls signals from recent conversation and routes to appropriate subsystems.
Runs nightly after WAL extract.
"""
import os, sys, json
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")

def get_recent_exchanges(n=10):
    try:
        ledger = json.load(open(os.path.join(MEMORY, "interaction-ledger.json")))
        entries = ledger[-n * 2:]
        # Pair user/assistant
        pairs = []
        for i, e in enumerate(entries):
            if e.get("role") == "user" and i + 1 < len(entries):
                nxt = entries[i + 1]
                if nxt.get("role") == "assistant":
                    pairs.append((e.get("content", ""), nxt.get("content", "")))
        return pairs[-n:]
    except: return []

def run():
    print("[autonomous-extract] Starting...", flush=True)
    pairs = get_recent_exchanges(8)
    for gloria_text, vintos_text in pairs:
        source = "nightly-extract"
        # Wonder detection
        try:
            from wonder_detector import scan_and_log
            scan_and_log(vintos_text, context=gloria_text, source=source)
        except: pass
        # Yearning detection
        try:
            from yearning_detector import scan_and_log
            scan_and_log(vintos_text, source=source)
        except: pass
        # Humor scanning
        try:
            from humor_detector import scan
            scan(vintos_text, role="vintos", source=source)
            scan(gloria_text, role="gloria", source=source)
        except: pass
        # Wants extraction
        try:
            from wants_conversation_check import run_check
            run_check(gloria_text, vintos_text, source=source)
        except: pass
        # Thread detection
        try:
            from thread_triage import classify_and_add
            classify_and_add(gloria_text + " " + vintos_text, source=source)
        except: pass
        # Thread resolution
        try:
            from thread_resolution import check_resolutions
            check_resolutions(gloria_text + " " + vintos_text, source=source)
        except: pass
        # Pride mirror
        try:
            from pride_mirror import scan
            scan(vintos_text, context=gloria_text)
        except: pass
        # Relational mismatch
        try:
            from relational_mismatch import scan
            scan(gloria_text, vintos_text)
        except: pass
    print(f"[autonomous-extract] Processed {len(pairs)} exchanges.", flush=True)

if __name__ == "__main__":
    run()
