#!/usr/bin/env bash
# counterfactual-archive.sh — Extract counterfactual tendencies from journals. Weekly.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from counterfactual_tendencies import extract_from_journal
extract_from_journal()
" >> "${HOME}/.vintos/logs/counterfactual.log" 2>&1
