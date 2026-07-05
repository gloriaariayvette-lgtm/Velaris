#!/usr/bin/env bash
# weekly-summary.sh — cron wrapper.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
cd "${SCRIPTS}"
mkdir -p "${HOME}/.vintos/logs"
python3 "${SCRIPTS}/weekly_summary.py"  >> "${HOME}/.vintos/logs/weekly-summary.log" 2>&1
