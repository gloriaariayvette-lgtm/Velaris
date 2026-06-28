#!/usr/bin/env bash
# voice-coherence.sh — Weekly voice coherence analysis.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from voice_coherence import analyze_voice_pattern
result = analyze_voice_pattern()
if result:
    print(f'[voice-coherence] {result[:80]}')
" >> "${HOME}/.vintos/logs/voice-coherence.log" 2>&1
