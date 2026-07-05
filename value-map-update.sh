#!/usr/bin/env bash
# value-map-update.sh — cron wrapper.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
cd "${SCRIPTS}"
mkdir -p "${HOME}/.vintos/logs"
python3 "${SCRIPTS}/value_map.py"  >> "${HOME}/.vintos/logs/value-map.log" 2>&1
