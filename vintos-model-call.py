#!/usr/bin/env python3
"""
vintos-model-call.py — Core Grok API call wrapper.
Reads system prompt from /tmp/vm_sys.txt, user prompt from /tmp/vm_usr.txt.
Injects subconscious context and EmoClaw pressure automatically.
"""
import os, sys, requests

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_config import VINTOS_MODEL, GROK_API, auth_headers

_SUBCON = ""
try:
    from subconscious_context import get_subconscious_context_compact
    _SUBCON = get_subconscious_context_compact()
except:
    pass

_EMO = ""
try:
    from emoclaw_pressure import get_pressure_block
    _EMO = get_pressure_block()
except:
    pass

sys_msg = open("/tmp/vm_sys.txt").read()
usr_msg = open("/tmp/vm_usr.txt").read()

if _SUBCON:
    sys_msg = sys_msg + "\n\n" + _SUBCON
if _EMO:
    sys_msg = sys_msg + "\n\n" + _EMO

r = requests.post(GROK_API, json={
    "model": VINTOS_MODEL,
    "messages": [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": usr_msg}
    ],
    "temperature": 0.85,
    "max_tokens": 4096
}, headers=auth_headers(), timeout=120)
r.raise_for_status()
print(r.json()["choices"][0]["message"]["content"].strip())
