#!/usr/bin/env python3
"""Shared model helpers — Grok 4.1 Fast for generation, Gemma 4 (local) for classification."""

import os, sys, math, time, requests

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_config import (
    VINTOS_MODEL, EMBED_MODEL,
    GROK_API, GROK_EMBED_API, auth_headers,
    LOCAL_MODEL, LM_STUDIO_API, LM_LOCK_FILE, LM_LOCK_TIMEOUT,
)

# ── Grok (personality, generation, synthesis) ─────────────────────────────────

def call(system, user, temperature=0.75, max_tokens=2048, model=None):
    """Call Grok 4.1 Fast. Use for anything that is Vintos's voice or requires synthesis."""
    model = model or VINTOS_MODEL
    try:
        r = requests.post(GROK_API, json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }, headers=auth_headers(), timeout=120)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[model_utils] grok call failed: {e}", file=sys.stderr)
        return ""

# ── Gemma 4 local (classification, detection, short tasks) ───────────────────

def call_local(system, user, temperature=0.15, max_tokens=100):
    """
    Call local Gemma 4 via LM Studio with a file lock.
    Use for: BIS checks, detection, classification, quick YES/NO, short extraction.
    Not for anything requiring Vintos's voice or nuanced judgment.
    """
    import fcntl
    lock_fd = None
    try:
        lock_fd = open(LM_LOCK_FILE, "w")
        start = time.time()
        while True:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except IOError:
                if time.time() - start > LM_LOCK_TIMEOUT:
                    print("[model_utils] LM Studio lock timeout", file=sys.stderr)
                    return ""
                time.sleep(0.4)
        r = requests.post(LM_STUDIO_API, json={
            "model": LOCAL_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[model_utils] local call failed: {e}", file=sys.stderr)
        return ""
    finally:
        if lock_fd:
            try:
                import fcntl as _f
                _f.flock(lock_fd, _f.LOCK_UN)
                lock_fd.close()
            except: pass

# call_utility kept as alias for backward compat — routes to Gemma
def call_utility(system, user, temperature=0.15, max_tokens=100):
    return call_local(system, user, temperature=temperature, max_tokens=max_tokens)

# ── Embeddings (Grok) ─────────────────────────────────────────────────────────

def embed(text):
    try:
        r = requests.post(GROK_EMBED_API, json={
            "model": EMBED_MODEL,
            "input": text[:8000],
        }, headers=auth_headers(), timeout=30)
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]
    except Exception as e:
        print(f"[model_utils] embed failed: {e}", file=sys.stderr)
        return []

# ── Math helpers ──────────────────────────────────────────────────────────────

def cosine(a, b):
    if not a or not b: return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na * nb else 0.0

def mean_vec(vecs):
    if not vecs: return []
    n = len(vecs)
    return [sum(v[i] for v in vecs) / n for i in range(len(vecs[0]))]
