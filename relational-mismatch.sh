#!/usr/bin/env bash
# relational-mismatch.sh — cron wrapper.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
cd "${SCRIPTS}"
mkdir -p "${HOME}/.vintos/logs"
python3 "${SCRIPTS}/relational_mismatch.py"  >> "${HOME}/.vintos/logs/relational-mismatch.log" 2>&1
