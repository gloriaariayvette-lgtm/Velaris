#!/bin/bash
# preoccupation-dream.sh — Third dream slot, ONLY fires if preoccupation exists
# Runs at 1:30 AM. If no preoccupation, exits silently.
# Forces the dream topic to be the preoccupation itself.

WORKSPACE="$HOME/.openclaw/workspace"

# Check if preoccupation exists
HAS_PREOCCUPATION=$(python3 << 'PYEOF'
import sys, os
sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace"))
try:
    from scripts.emoclaw_utils import get_preoccupation
    p = get_preoccupation()
    if p and p.get("thread"):
        print(p["thread"])
    else:
        print("")
except:
    print("")
PYEOF
)

if [ -z "$HAS_PREOCCUPATION" ]; then
    exit 0
fi

echo "[PreoccupationDream] Unresolved preoccupation detected, forcing third dream"
echo "[PreoccupationDream] Thread: $HAS_PREOCCUPATION"

# Override dream state to allow a third dream
STATE_FILE="$WORKSPACE/skills/dreaming/data/dream-state.json"
if [ -f "$STATE_FILE" ]; then
    python3 -c "
import json
with open('$STATE_FILE') as f: s = json.load(f)
s['maxDreamsPerNight'] = 3
with open('$STATE_FILE', 'w') as f: json.dump(s, f)
"
fi

# Trigger dream with the preoccupation as topic
FORCED_TOPIC="preoccupation:$HAS_PREOCCUPATION" bash "$WORKSPACE/skills/dreaming/scripts/dream-trigger.sh"

# Reset max back to 2
if [ -f "$STATE_FILE" ]; then
    python3 -c "
import json
with open('$STATE_FILE') as f: s = json.load(f)
s['maxDreamsPerNight'] = 2
with open('$STATE_FILE', 'w') as f: json.dump(s, f)
"
fi
