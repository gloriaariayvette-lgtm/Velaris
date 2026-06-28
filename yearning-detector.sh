#!/usr/bin/env bash
# yearning-detector.sh — Scan recent exchanges for yearning. Daily.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys, json, os
sys.path.insert(0, '${SCRIPTS}')
from yearning_detector import scan_and_log
MEMORY = os.path.expanduser('~/.vintos/workspace/memory')
try:
    ledger = json.load(open(os.path.join(MEMORY, 'interaction-ledger.json')))
    for e in ledger[-10:]:
        if e.get('role') == 'assistant':
            scan_and_log(e.get('content',''), source='daily-cron')
except Exception as ex:
    print(f'Error: {ex}')
" >> "${HOME}/.vintos/logs/yearning.log" 2>&1
