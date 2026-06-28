#!/usr/bin/env bash
# absence-map.sh — Weekly absence scan.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from absence_map_cold import run_absence_scan
run_absence_scan()
" >> "${HOME}/.vintos/logs/absence-map.log" 2>&1
