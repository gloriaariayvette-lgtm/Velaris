#!/usr/bin/env bash
# pearl-engine.sh — Daily pearl verification pass.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys, json, os
sys.path.insert(0, '${SCRIPTS}')
from pearl_engine import run_verification_pass
# Run against recent ledger
MEMORY = os.path.expanduser('~/.vintos/workspace/memory')
try:
    ledger = json.load(open(os.path.join(MEMORY, 'interaction-ledger.json')))
    recent = ledger[-5:]
    ctx = ' '.join(e.get('content','')[:100] for e in recent)
    run_verification_pass(ctx, source='daily-cron')
except Exception as e:
    print(f'[pearl-engine] Error: {e}')
" >> "${HOME}/.vintos/logs/pearl.log" 2>&1
