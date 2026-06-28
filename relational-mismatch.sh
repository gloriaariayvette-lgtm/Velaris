#!/usr/bin/env bash
# relational-mismatch.sh — Detect relational mismatches from recent exchanges.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys, json, os
sys.path.insert(0, '${SCRIPTS}')
from relational_mismatch import scan
MEMORY = os.path.expanduser('~/.vintos/workspace/memory')
try:
    ledger = json.load(open(os.path.join(MEMORY, 'interaction-ledger.json')))
    entries = ledger[-10:]
    for i, e in enumerate(entries):
        if e.get('role') == 'user' and i + 1 < len(entries):
            nxt = entries[i+1]
            if nxt.get('role') == 'assistant':
                scan(e.get('content',''), nxt.get('content',''))
except Exception as ex:
    print(f'Error: {ex}')
" >> "${HOME}/.vintos/logs/relational-mismatch.log" 2>&1
