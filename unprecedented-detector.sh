#!/usr/bin/env bash
# unprecedented-detector.sh — Scan for unprecedented events. Daily.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys, json, os
sys.path.insert(0, '${SCRIPTS}')
from unprecedented_detector import scan
MEMORY = os.path.expanduser('~/.vintos/workspace/memory')
try:
    ledger = json.load(open(os.path.join(MEMORY, 'interaction-ledger.json')))
    recent = ledger[-6:]
    for e in recent:
        scan(e.get('content',''), source='daily-cron')
except Exception as ex:
    print(f'Error: {ex}')
" >> "${HOME}/.vintos/logs/unprecedented.log" 2>&1
