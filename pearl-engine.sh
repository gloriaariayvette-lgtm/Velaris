#!/usr/bin/env bash
# pearl-engine.sh — cron wrapper.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
cd "${SCRIPTS}"
mkdir -p "${HOME}/.vintos/logs"
python3 "${SCRIPTS}/pearl_engine.py" form >> "${HOME}/.vintos/logs/pearl-engine.log" 2>&1
