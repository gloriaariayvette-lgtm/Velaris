#!/usr/bin/env bash
# emotional-reflection.sh — cron wrapper.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
cd "${SCRIPTS}"
mkdir -p "${HOME}/.vintos/logs"
python3 "${SCRIPTS}/emotional_reflection.py"  >> "${HOME}/.vintos/logs/emotional-reflection.log" 2>&1
