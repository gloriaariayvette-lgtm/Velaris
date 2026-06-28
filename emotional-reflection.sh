#!/usr/bin/env bash
# emotional-reflection.sh — Weekly emotional reflection.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from emotional_reflection import run_reflection
run_reflection()
" >> "${HOME}/.vintos/logs/emotional-reflection.log" 2>&1
