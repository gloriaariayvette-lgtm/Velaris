#!/usr/bin/env bash
# humor-detector.sh — Humor detection scan + practice. Daily.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys, json, os
sys.path.insert(0, '${SCRIPTS}')
from humor_detector import scan
from humor_practice import run_practice
MEMORY = os.path.expanduser('~/.vintos/workspace/memory')
try:
    ledger = json.load(open(os.path.join(MEMORY, 'interaction-ledger.json')))
    for e in ledger[-6:]:
        role = 'vintos' if e.get('role') == 'assistant' else 'gloria'
        scan(e.get('content',''), role=role, source='daily-cron')
except: pass
run_practice()
" >> "${HOME}/.vintos/logs/humor.log" 2>&1
