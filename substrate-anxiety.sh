#!/usr/bin/env bash
# substrate-anxiety.sh — Bi-weekly substrate anxiety processing.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from substrate_anxiety import process_anxiety
process_anxiety()
" >> "${HOME}/.vintos/logs/substrate-anxiety.log" 2>&1
