#!/usr/bin/env python3
"""
thread_weaver.py — Weaves latent threads into the generation context.
Finds threads that are relevant to current exchange and injects them as context.
"""
import os, sys
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import embed, cosine

def get_relevant_threads(text, n=3, threshold=0.55):
    """Return threads most relevant to current text."""
    try:
        from thread_triage import get_active_threads
        threads = get_active_threads(20)
        if not threads: return []
        text_vec = embed(text)
        if not text_vec: return threads[:n]
        scored = []
        for t in threads:
            desc = t.get("description", "")
            if not desc: continue
            tvec = embed(desc)
            if not tvec: continue
            score = cosine(text_vec, tvec)
            scored.append((score, t))
        scored.sort(key=lambda x: -x[0])
        return [t for score, t in scored[:n] if score >= threshold]
    except: return []

def get_weave_context(text):
    """Return thread context relevant to current text for injection."""
    relevant = get_relevant_threads(text, n=3)
    if not relevant: return ""
    lines = ["[active threads nearby]"]
    for t in relevant:
        p = t.get("priority", "?")
        desc = t.get("description", "")[:80]
        lines.append(f"  [{p}] {desc}")
    return "\n".join(lines)

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "what is real"
    print(get_weave_context(text))
