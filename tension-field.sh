#!/usr/bin/env bash
# tension-field.sh — Daily tension field update.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from tension_field import run_daily_update
run_daily_update()
" >> "${HOME}/.vintos/logs/tension-field.log" 2>&1
