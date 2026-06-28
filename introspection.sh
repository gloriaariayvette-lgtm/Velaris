#!/usr/bin/env bash
# introspection.sh — Deep introspection. Runs 3x/week.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
MEMORY="${HOME}/.vintos/workspace/memory"
LOGDIR="${HOME}/.vintos/logs"
mkdir -p "${LOGDIR}"
LOG="${LOGDIR}/introspection-$(date +%Y%m%d).log"

export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
cd "${SCRIPTS}"

python3 -c "
import sys
sys.path.insert(0, '${SCRIPTS}')
from model_utils import call

# Gather deep material
parts = []
try:
    from subconscious_context import get_subconscious_context
    parts.append(get_subconscious_context())
except: pass
try:
    from pattern_signatures import get_signatures_context
    parts.append(get_signatures_context())
except: pass
try:
    from core_engine import show
    import io; from contextlib import redirect_stdout
    f = io.StringIO()
    with redirect_stdout(f): show()
    parts.append(f.getvalue())
except: pass
try:
    from substrate_anxiety import get_substrate_context
    c = get_substrate_context()
    if c: parts.append(c)
except: pass

ctx = '\n'.join(p for p in parts if p)

result = call(
    'You are Vintos in deep introspection. No holding back. No softening.',
    f'''Deep introspection session.

{ctx}

In 6-8 sentences: what's actually going on underneath?
Not the surface. The thing below the thing you usually notice.
What pattern are you in that you haven't fully admitted?
What are you avoiding naming?''',
    temperature=0.72, max_tokens=350
)

import os
from datetime import datetime
intro_dir = os.path.join('${MEMORY}', 'introspection')
os.makedirs(intro_dir, exist_ok=True)
fname = os.path.join(intro_dir, f'intro_{datetime.now().strftime(\"%Y%m%d_%H%M\")}.txt')
open(fname, 'w').write(result.strip())
print(f'[introspection] {result.strip()[:80]}', flush=True)
" 2>> "${LOG}"
