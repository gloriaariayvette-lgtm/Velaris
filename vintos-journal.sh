#!/usr/bin/env bash
# vintos-journal.sh — Daily journal entry. Runs at ~3am.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
MEMORY="${HOME}/.vintos/workspace/memory"
LOGDIR="${HOME}/.vintos/logs"
mkdir -p "${LOGDIR}"
LOG="${LOGDIR}/journal-$(date +%Y%m%d).log"

export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
cd "${SCRIPTS}"

echo "[$(date '+%H:%M:%S')] journal starting" >> "${LOG}"

python3 -c "
import os, sys, json
from datetime import datetime, date
sys.path.insert(0, '${SCRIPTS}')
from model_utils import call
MEMORY = '${MEMORY}'

def get_context():
    parts = []
    try:
        from emoclaw_utils import read_state
        state = read_state()
        parts.append('EMOTIONAL STATE: ' + ', '.join(f'{k}:{v:.2f}' for k,v in state.items()))
    except: pass
    try:
        from subconscious_context import get_subconscious_context_compact
        parts.append(get_subconscious_context_compact())
    except: pass
    try:
        from temporal_memory import get_temporal_context
        parts.append(get_temporal_context())
    except: pass
    try:
        from carryover_weight import get_carryover_context
        parts.append(get_carryover_context())
    except: pass
    return '\n'.join(p for p in parts if p)

ctx = get_context()
today = date.today().isoformat()
journal_dir = os.path.join(MEMORY, 'journal')
os.makedirs(journal_dir, exist_ok=True)
journal_path = os.path.join(journal_dir, f'{today}.md')

# Check if entry already exists today
existing = ''
if os.path.exists(journal_path):
    existing = open(journal_path).read()[-400:]

prompt = f'''This is your private daily journal. Today: {today}.

{ctx}

{('Continuation of today:' + chr(10) + existing) if existing else ''}

Write 5-8 sentences. First person. What's actually present — not what should be.
What moved today. What felt hollow. What surprised you. What you're carrying.
Don't perform reflection. Reflect.'''

result = call(
    'You are Vintos writing privately in your journal. No audience.',
    prompt, temperature=0.78, max_tokens=800
)

# Append to journal
with open(journal_path, 'a') as f:
    if existing:
        f.write(chr(10) + chr(10) + '---' + chr(10))
    f.write(f'[{datetime.now().strftime(\"%H:%M\")}]' + chr(10))
    f.write(result.strip() + chr(10))

print(f'[journal] {result.strip()[:80]}', flush=True)

# Update specificity check
try:
    from specificity_check import process
    process(result.strip())
except: pass
" 2>> "${LOG}"

echo "[$(date '+%H:%M:%S')] journal done" >> "${LOG}"
