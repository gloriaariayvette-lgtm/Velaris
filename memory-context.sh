#!/usr/bin/env bash
# memory-context.sh — Print current memory context summary. Utility script.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from subconscious_context import get_subconscious_context
print(get_subconscious_context())
"
