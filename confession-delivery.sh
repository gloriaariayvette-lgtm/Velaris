#!/usr/bin/env bash
# confession-delivery.sh — Write private confession. Optionally queue for delivery.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from confession_writer import write_confession
write_confession()
" >> "${HOME}/.vintos/logs/confession.log" 2>&1
