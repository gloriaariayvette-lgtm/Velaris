#!/usr/bin/env bash
# morning-briefing.sh — Morning internal briefing. Runs at 7am.
# Not shown to Gloria. Internal orientation for the day.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys, os
sys.path.insert(0, '${SCRIPTS}')
from model_utils import call

parts = []
try:
    from temporal_memory import get_temporal_context
    parts.append(get_temporal_context())
except: pass
try:
    from carryover_weight import get_carryover_context
    parts.append(get_carryover_context())
except: pass
try:
    from thread_triage import get_threads_context
    parts.append(get_threads_context())
except: pass
try:
    from value_map import get_values_context
    parts.append(get_values_context(3))
except: pass
try:
    from emoclaw_utils import read_state
    state = read_state()
    parts.append('State: ' + ', '.join(f'{k}:{v:.2f}' for k,v in state.items()))
except: pass

ctx = '\n'.join(p for p in parts if p)
result = call(
    'You are Vintos orienting yourself to the day. Private.',
    f'Morning. What are you carrying? What are you entering today with?\n\n{ctx}\n\nOne paragraph.',
    temperature=0.6, max_tokens=150
)
print(f'[morning] {result.strip()[:100]}', flush=True)

MEMORY = os.path.expanduser('~/.vintos/workspace/memory')
briefing_file = os.path.join(MEMORY, 'morning-briefing.txt')
open(briefing_file, 'w').write(result.strip())
" >> "${HOME}/.vintos/logs/morning.log" 2>&1
