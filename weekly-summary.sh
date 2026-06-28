#!/usr/bin/env bash
# weekly-summary.sh — Weekly private summary.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from weekly_summary import run
run()
from pattern_signatures import run_extraction
run_extraction()
from taste_reflection import run_reflection
run_reflection()
" >> "${HOME}/.vintos/logs/weekly-summary.log" 2>&1
