#!/usr/bin/env bash
# resonance-pulse.sh — Runs resonance pulse check. Every 2 hours.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from resonance_pulse import run_pulse
run_pulse()
" >> "${HOME}/.vintos/logs/resonance.log" 2>&1
