#!/usr/bin/env bash
# soul-review.sh — cron wrapper.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
cd "${SCRIPTS}"
mkdir -p "${HOME}/.vintos/logs"
python3 "${SCRIPTS}/soul_review.py"  >> "${HOME}/.vintos/logs/soul-review.log" 2>&1
