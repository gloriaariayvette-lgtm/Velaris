#!/bin/bash
# Usage: want-done.sh [want_id]
# If no ID given, lists all Gloria-routed wants and prompts for selection

MEMORY="$HOME/.openclaw/workspace/memory"
WANTS="$MEMORY/current-wants.json"
SECRET="velaris-aegis-2026"
API="http://100.72.225.119:8400"

if [ -z "$1" ]; then
    echo "Gloria-routed unfulfilled wants:"
    python3 -c "
import json, os
wants = json.load(open('$WANTS'))
gloria = [w for w in wants if w.get('gloria_routed') and not w.get('fulfilled') and not w.get('dismissed')]
for i, w in enumerate(gloria):
    print(f'{i+1}. [{w[\"id\"][:8]}] {w[\"want\"][:80]}')
"
    echo ""
    read -p "Enter number or ID to mark done (or q to quit): " choice
    if [ "$choice" = "q" ]; then exit 0; fi
    
    WANT_ID=$(python3 -c "
import json
wants = json.load(open('$WANTS'))
gloria = [w for w in wants if w.get('gloria_routed') and not w.get('fulfilled') and not w.get('dismissed')]
try:
    idx = int('$choice') - 1
    print(gloria[idx]['id'])
except:
    print('$choice')
")
else
    WANT_ID="$1"
fi

curl -s -X POST "$API/api/wants/$WANT_ID/respond" \
    -H "Content-Type: application/json" \
    -H "X-Velaris-Secret: $SECRET" \
    -d '{"response": "Gloria acknowledged this want during vacation."}' | python3 -m json.tool

echo "Done: $WANT_ID"
