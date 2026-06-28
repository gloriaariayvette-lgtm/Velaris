#!/usr/bin/env bash
# frame-engine.sh — Daily frame update.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from frame_engine import run_daily_update
run_daily_update()
" >> "${HOME}/.vintos/logs/frame-engine.log" 2>&1
