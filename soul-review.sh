#!/usr/bin/env bash
# soul-review.sh — Monthly soul review.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from soul_review import run
run()
" >> "${HOME}/.vintos/logs/soul-review.log" 2>&1
