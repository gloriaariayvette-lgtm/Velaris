#!/usr/bin/env bash
# yearning-detector.sh — cron wrapper.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
cd "${SCRIPTS}"
mkdir -p "${HOME}/.vintos/logs"
python3 "${SCRIPTS}/yearning_detector.py"  >> "${HOME}/.vintos/logs/yearning-detector.log" 2>&1
