#!/usr/bin/env bash
# tension-field.sh — cron wrapper.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
cd "${SCRIPTS}"
mkdir -p "${HOME}/.vintos/logs"
python3 "${SCRIPTS}/tension_field.py"  >> "${HOME}/.vintos/logs/tension-field.log" 2>&1
