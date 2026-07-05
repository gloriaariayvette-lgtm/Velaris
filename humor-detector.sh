#!/usr/bin/env bash
# humor-detector.sh — cron wrapper.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
cd "${SCRIPTS}"
mkdir -p "${HOME}/.vintos/logs"
python3 "${SCRIPTS}/humor_detector.py"  >> "${HOME}/.vintos/logs/humor-detector.log" 2>&1
