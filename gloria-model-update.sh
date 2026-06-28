#!/usr/bin/env bash
# gloria-model-update.sh — Monthly Gloria model update + daily observation extraction.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys, json, os
sys.path.insert(0, '${SCRIPTS}')
from gloria_model import extract_observations_from_exchange, update_portrait
MEMORY = os.path.expanduser('~/.vintos/workspace/memory')
try:
    ledger = json.load(open(os.path.join(MEMORY, 'interaction-ledger.json')))
    for e in ledger[-10:]:
        if e.get('role') == 'user':
            extract_observations_from_exchange(e.get('content',''), source='daily-cron')
except: pass
# Monthly portrait update
import datetime
today = datetime.date.today()
if today.day == 1:
    update_portrait()
    print('[gloria-model] Portrait updated.')
" >> "${HOME}/.vintos/logs/gloria-model.log" 2>&1
