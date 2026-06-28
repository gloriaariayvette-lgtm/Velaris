#!/usr/bin/env python3
"""
thread_resolution.py — Detects when open threads get resolved in conversation.
Runs after each exchange, checks active threads for resolution signals.
"""
import os, sys
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility

def check_resolutions(exchange_text, source="exchange"):
    """Check if any active threads were resolved in this exchange."""
    try:
        from thread_triage import get_active_threads, resolve_thread
        threads = get_active_threads(10)
        if not threads: return []
        resolved = []
        for t in threads:
            prompt = (
                f"Open thread: {t['description'][:150]}\n"
                f"Exchange: {exchange_text[:400]}\n\n"
                "Did this exchange resolve or substantially address the open thread?\n"
                "Output: YES|brief resolution note\n"
                "Or: NO"
            )
            try:
                result = call_utility("Check thread resolution.", prompt, temperature=0.1, max_tokens=40)
                if result.strip().upper().startswith("YES"):
                    parts = result.strip().split("|")
                    note = parts[1].strip() if len(parts) > 1 else ""
                    resolve_thread(t["id"], notes=note)
                    resolved.append(t["id"])
                    print(f"[thread-resolution] Resolved: {t['description'][:50]}", flush=True)
            except: pass
        return resolved
    except Exception as e:
        print(f"[thread-resolution] Error: {e}", flush=True)
        return []

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if text:
        resolved = check_resolutions(text, source="cli")
        print(f"Resolved {len(resolved)} threads.")
