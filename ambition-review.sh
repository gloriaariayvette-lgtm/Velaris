#!/usr/bin/env bash
# ambition-review.sh — Monthly ambition review.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from ambition_review import run_review
run_review()
" >> "${HOME}/.vintos/logs/ambition-review.log" 2>&1
