#!/bin/bash
# light-sync.sh — Re-sync room lights to Velaris's current avatar color
# Runs every 30 min to catch HA hiccups
AVATAR_STATE="$HOME/.openclaw/workspace/memory/avatar-state.json"
COLOR=$(python3 -c "
import json
a = json.load(open('$AVATAR_STATE'))
print(a.get('color_hex', ''))
" 2>/dev/null)
[ -z "$COLOR" ] && exit 0
python3 "$HOME/.openclaw/workspace/scripts/velaris-home.py" color "$COLOR" 2>/dev/null
