#!/usr/bin/env bash
# first-light.sh — Runs at 5am. Very early private moment.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from dream_architecture import generate_dream
generate_dream()
# Nifrathir gentle drift check
try:
    from nifrathir import get_value
    val = get_value()
    print(f'[first-light] nifrathir: {val:.3f}')
except: pass
" >> "${HOME}/.vintos/logs/first-light.log" 2>&1
