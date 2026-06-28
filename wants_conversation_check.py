#!/usr/bin/env python3
"""
wants_conversation_check.py — Post-exchange check for wants expressed in conversation.
Runs after each exchange to catch and route wants from both sides.
"""
import os, sys
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

def run_check(gloria_text, vintos_text, source="exchange"):
    """Check both sides of an exchange for want expressions."""
    try:
        from wants_router import extract_wants_from_text
        gloria_wants = extract_wants_from_text(gloria_text, role="gloria", source=f"{source}-gloria")
        vintos_wants = extract_wants_from_text(vintos_text, role="vintos", source=f"{source}-vintos")
        total = len(gloria_wants) + len(vintos_wants)
        if total > 0:
            print(f"[wants-check] Found {total} want expressions", flush=True)
        return gloria_wants, vintos_wants
    except Exception as e:
        print(f"[wants-check] Error: {e}", flush=True)
        return [], []

if __name__ == "__main__":
    # CLI test
    gloria = sys.argv[1] if len(sys.argv) > 1 else ""
    vintos = sys.argv[2] if len(sys.argv) > 2 else ""
    if gloria or vintos:
        g, v = run_check(gloria, vintos, source="cli")
        print(f"Gloria wants: {g}")
        print(f"Vintos wants: {v}")
