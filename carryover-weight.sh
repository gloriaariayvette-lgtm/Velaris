#!/usr/bin/env bash
# carryover-weight.sh — Nightly carryover weight computation.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from carryover_weight import run
run()
" >> "${HOME}/.vintos/logs/carryover.log" 2>&1
