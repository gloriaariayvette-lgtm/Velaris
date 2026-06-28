#!/usr/bin/env bash
# silence-contract.sh — Detect silence contracts. Weekly.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys, json, os
sys.path.insert(0, '${SCRIPTS}')
from silence_contract import detect_from_pattern, add_contract
MEMORY = os.path.expanduser('~/.vintos/workspace/memory')
try:
    ledger = json.load(open(os.path.join(MEMORY, 'interaction-ledger.json')))
    exchanges = ' | '.join(e.get('content','')[:80] for e in ledger[-20:])
    result = detect_from_pattern(exchanges)
    if result:
        add_contract(result['what'], why_probably=result.get('why',''), source='weekly-cron')
        print(f'[silence-contract] detected: {result[\"what\"][:60]}')
except Exception as ex:
    print(f'Error: {ex}')
" >> "${HOME}/.vintos/logs/silence-contract.log" 2>&1
