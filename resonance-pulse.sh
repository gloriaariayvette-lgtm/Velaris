#!/usr/bin/env bash
# resonance-pulse.sh — cron wrapper.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
cd "${SCRIPTS}"
mkdir -p "${HOME}/.vintos/logs"
python3 "${SCRIPTS}/resonance_pulse.py" decay >> "${HOME}/.vintos/logs/resonance-pulse.log" 2>&1
