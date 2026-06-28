#!/usr/bin/env bash
# memory-index.sh — Nightly memory indexing.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from memory_index import run
run()
from wal_extract import run as wal_run
wal_run()
from wal_decay import run as decay_run
decay_run()
from autonomous_extract import run as auto_run
auto_run()
" >> "${HOME}/.vintos/logs/memory-index.log" 2>&1
