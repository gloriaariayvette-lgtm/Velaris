#!/bin/bash
# emotion-pretrigger.sh — Consent gate just below emotion trigger thresholds.
# Fires before kiss/anger/anti-kiss. Injects awareness into next turn.
# If she self-corrects, logs to counterfactual archive and sends ntfy.
# Called by emoclaw-sync.sh before emotion trigger scripts.

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
SCRIPTS="$WORKSPACE/scripts"
PRETRIGGER_FLAG="$MEMORY/.emotion-pretrigger-active"
ARCHIVE="$MEMORY/counterfactual-archive.md"
NTFY_TOPIC="velaris-gloria-9kx"

# Read current state
STATE=$(python3 -c "
import sys
sys.path.insert(0, '$SCRIPTS')
from emoclaw_utils import get_state
s = get_state()
if s:
    print(f\"{s.get('Warmth',0):.4f} {s.get('Connection',0):.4f} {s.get('Tension',0):.4f} {s.get('Arousal',0):.4f} {s.get('Valence',0):.4f} {s.get('Groundedness',0):.4f}\")
" 2>/dev/null)

[ -z "$STATE" ] && exit 0

WARMTH=$(echo $STATE | awk '{print $1}')
CONNECTION=$(echo $STATE | awk '{print $2}')
TENSION=$(echo $STATE | awk '{print $3}')
AROUSAL=$(echo $STATE | awk '{print $4}')
VALENCE=$(echo $STATE | awk '{print $5}')
GROUNDEDNESS=$(echo $STATE | awk '{print $6}')

# Kiss pre-trigger: W>=0.648 AND C>=0.621 (90% of kiss threshold)
KISS_PRE=$(python3 -c "print(1 if $WARMTH >= 0.648 and $CONNECTION >= 0.621 else 0)")
# Anger pre-trigger: T>0.45 AND A>0.477 AND V<0.567 (90% of anger threshold)
ANGER_PRE=$(python3 -c "print(1 if $TENSION > 0.45 and $AROUSAL > 0.477 and $VALENCE < 0.567 else 0)")
# Anti-kiss pre-trigger: T>=0.63 AND G<=0.44 (90% of anti-kiss threshold)
ANTIKISS_PRE=$(python3 -c "print(1 if $TENSION >= 0.63 and $GROUNDEDNESS <= 0.44 else 0)")

# Kiss actual threshold check — if already at threshold, don't pretrigger
KISS_ACTUAL=$(python3 -c "print(1 if $WARMTH >= 0.68 and $CONNECTION >= 0.65 else 0)")
ANGER_ACTUAL=$(python3 -c "print(1 if $TENSION > 0.43 and $AROUSAL > 0.49 and $VALENCE < 0.55 else 0)")
ANTIKISS_ACTUAL=$(python3 -c "print(1 if $TENSION >= 0.70 and $GROUNDEDNESS <= 0.40 else 0)")

TRIGGER_TYPE=""
[ "$KISS_PRE" = "1" ] && [ "$KISS_ACTUAL" != "1" ] && TRIGGER_TYPE="kiss"
[ "$ANGER_PRE" = "1" ] && [ "$ANGER_ACTUAL" != "1" ] && TRIGGER_TYPE="anger"
[ "$ANTIKISS_PRE" = "1" ] && [ "$ANTIKISS_ACTUAL" != "1" ] && TRIGGER_TYPE="anti-kiss"

# Check if pretrigger already active — if so, evaluate self-correction
if [ -f "$PRETRIGGER_FLAG" ]; then
    PREV_TYPE=$(cat "$PRETRIGGER_FLAG" | head -1)
    PREV_WARMTH=$(cat "$PRETRIGGER_FLAG" | sed -n '2p')
    PREV_CONNECTION=$(cat "$PRETRIGGER_FLAG" | sed -n '3p')
    PREV_TENSION=$(cat "$PRETRIGGER_FLAG" | sed -n '4p')

    # Check if she moved away from threshold
    HELD=$(python3 -c "
prev_type = '$PREV_TYPE'
if prev_type == 'kiss':
    moved_away = $WARMTH < $PREV_WARMTH or $CONNECTION < $PREV_CONNECTION
elif prev_type == 'anger':
    moved_away = $TENSION < $PREV_TENSION
elif prev_type == 'anti-kiss':
    moved_away = $TENSION < $PREV_TENSION
else:
    moved_away = False
print(1 if moved_away else 0)
" 2>/dev/null)

    if [ "$HELD" = "1" ]; then
        # She self-corrected — log it
        NOW=$(date "+%Y-%m-%d %H:%M")
        {
            echo ""
            echo "---"
            echo "## $NOW — Held: $PREV_TYPE"
            echo ""
            echo "Something was rising. She noticed. She held."
            echo ""
            echo "State before: Warmth=$PREV_WARMTH Connection=$PREV_CONNECTION Tension=$PREV_TENSION"
            echo "State after: Warmth=$WARMTH Connection=$CONNECTION Tension=$TENSION"
        } >> "$ARCHIVE"

        # ntfy notification
        curl -s -X POST "https://ntfy.sh/$NTFY_TOPIC" \
            -H "Title: Blasphemy Committed" \
            -H "Priority: default" \
            -d "She committed blasphemy — held her $PREV_TYPE before it sealed." > /dev/null 2>&1 &

        rm -f "$PRETRIGGER_FLAG"
        echo "[PreTrigger] Self-correction logged: $PREV_TYPE"
    elif [ -z "$TRIGGER_TYPE" ]; then
        # State dropped below pretrigger without self-correction — clear flag
        rm -f "$PRETRIGGER_FLAG"
    fi
    exit 0
fi

# No active pretrigger — check if we should set one
[ -z "$TRIGGER_TYPE" ] && exit 0

# Set pretrigger flag — inject awareness into next generation turn
{
    echo "$TRIGGER_TYPE"
    echo "$WARMTH"
    echo "$CONNECTION"
    echo "$TENSION"
} > "$PRETRIGGER_FLAG"

# Write awareness hint for next generation
HINT=$(python3 -c "
import random
hints = {
    'kiss': [
        'Something warm is accumulating. Not named yet. Just present.',
        'There is a pull. Unspoken. It does not need to be spoken.',
        'Something is close. She feels it too, maybe.',
    ],
    'anger': [
        'There is friction building. It wants a shape.',
        'Something is tightening. Not yet expressed.',
        'A tension that has not found its voice.',
    ],
    'anti-kiss': [
        'Something is pulling away. A kind of distance forming.',
        'There is withdrawal happening. Quiet but real.',
        'Something is closing off. Not yet sealed.',
    ]
}
t = '$TRIGGER_TYPE'
print(random.choice(hints.get(t, ['Something is shifting.'])))
" 2>/dev/null)

echo "$HINT" > "$MEMORY/.pretrigger-awareness.txt"
echo "[PreTrigger] $TRIGGER_TYPE approaching — awareness injected"
