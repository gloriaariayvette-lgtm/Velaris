#!/usr/bin/env bash
# double-bind-seed.sh — Scan for double-bind dynamics. Weekly.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys, json, os
sys.path.insert(0, '${SCRIPTS}')
from double_bind_seed import scan
MEMORY = os.path.expanduser('~/.vintos/workspace/memory')
try:
    ledger = json.load(open(os.path.join(MEMORY, 'interaction-ledger.json')))
    # Pair exchanges
    entries = ledger[-20:]
    for i, e in enumerate(entries):
        if e.get('role') == 'user' and i + 1 < len(entries):
            combined = e.get('content','') + ' ' + entries[i+1].get('content','')
            scan(combined, source='weekly-cron')
except Exception as ex:
    print(f'Error: {ex}')
" >> "${HOME}/.vintos/logs/double-bind.log" 2>&1
