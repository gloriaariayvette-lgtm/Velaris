#!/usr/bin/env bash
# value-map-update.sh — Weekly value map update.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from value_map import update_from_context
update_from_context()
" >> "${HOME}/.vintos/logs/value-map.log" 2>&1
