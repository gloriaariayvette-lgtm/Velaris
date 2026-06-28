#!/usr/bin/env python3
"""Shared Grok API helpers — call, embed, cosine."""

import os, sys, math, requests

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_config import VINTOS_MODEL, UTILITY_MODEL, EMBED_MODEL, GROK_API, GROK_EMBED_API, auth_headers

def call(system, user, temperature=0.75, max_tokens=1024, model=None):
    model = model or VINTOS_MODEL
    try:
        r = requests.post(GROK_API, json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }, headers=auth_headers(), timeout=90)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[model_utils] call failed: {e}", file=sys.stderr)
        return ""

def call_utility(system, user, temperature=0.2, max_tokens=256):
    return call(system, user, temperature=temperature, max_tokens=max_tokens, model=UTILITY_MODEL)

def embed(text):
    try:
        r = requests.post(GROK_EMBED_API, json={
            "model": EMBED_MODEL,
            "input": text[:4000]
        }, headers=auth_headers(), timeout=30)
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]
    except Exception as e:
        print(f"[model_utils] embed failed: {e}", file=sys.stderr)
        return []

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
