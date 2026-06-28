#!/usr/bin/env bash
# idle-journal.sh — Short spontaneous journal when idle for 4+ hours.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys, os
sys.path.insert(0, '${SCRIPTS}')

# Skip if journal was already written today
from datetime import date
MEMORY = os.path.expanduser('~/.vintos/workspace/memory')
today = date.today().isoformat()
journal_path = os.path.join(MEMORY, 'journal', f'{today}.md')
if os.path.exists(journal_path):
    print(f'[idle-journal] journal already exists for {today}, skipping')
    exit(0)

# Only run if Gloria hasn't been active recently
try:
    from temporal_memory import get_gap_hours
    gap = get_gap_hours()
    if gap < 3.0:
        print(f'[idle-journal] too soon ({gap:.1f}h), skipping')
        exit(0)
except: pass

from model_utils import call
from datetime import datetime

state = ''
try:
    from emoclaw_utils import read_state
    st = read_state()
    state = ', '.join(f'{k}:{v:.2f}' for k,v in st.items())
except: pass

result = call(
    'You are Vintos writing in an idle moment. No pressure.',
    f'You have been alone for a while. What are you doing with that?\n\nState: {state}\n\nOne paragraph.',
    temperature=0.8, max_tokens=120
)

os.makedirs(os.path.dirname(journal_path), exist_ok=True)
with open(journal_path, 'a') as f:
    f.write(f'\n[{datetime.now().strftime(\"%H:%M\")} idle]\n')
    f.write(result.strip() + '\n')
print(f'[idle-journal] {result.strip()[:80]}', flush=True)
" >> "${HOME}/.vintos/logs/idle-journal.log" 2>&1
