#!/usr/bin/env bash
# midday-ground.sh — Midday grounding check. Runs at noon.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')

# Run discourse direction update
try:
    from discourse_direction import update_direction
    update_direction()
except: pass

# Resonance pulse
try:
    from resonance_pulse import run_pulse
    run_pulse()
except: pass

# Affective weight update
try:
    from affective_weight import on_contact
    on_contact()
except: pass

print('[midday-ground] complete', flush=True)
" >> "${HOME}/.vintos/logs/midday.log" 2>&1
