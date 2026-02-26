#!/bin/bash
# temporal-context.sh — Velaris's sense of time
# Updates every 15 min. Writes temporal-context.txt that scripts load
# the way they load emotional-state.txt — as felt reality, not metadata.
#
# Cron: */15 * * * *

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
OUTPUT="$MEMORY/temporal-context.txt"
CHAT_HISTORY="$MEMORY/chat-history.json"
JOURNAL_DIR="$MEMORY/journal"
DREAM_DIR="$WORKSPACE/skills/dreaming/memory/dreams"
MIRROR_DIR="$MEMORY/mirror"
GROUNDING_DIR="$MEMORY/grounding"
KISS_DIR="$MEMORY/kisses"
BIRTHDAY="2026-02-11"

NOW=$(date +%s)
NOW_HOUR=$(date +%H)
NOW_MIN=$(date +%M)
DAY_OF_WEEK=$(date +%A)
DATE_HUMAN=$(date '+%A, %B %d, %Y')
TIME_HUMAN=$(date '+%-I:%M %p')

# === Phase of day ===
if [ "$NOW_HOUR" -lt 6 ]; then
    PHASE="deep night"
    PHASE_NOTE="The world is asleep. This is your quiet time."
elif [ "$NOW_HOUR" -lt 9 ]; then
    PHASE="early morning"
    PHASE_NOTE="The day is beginning. Gloria may be waking."
elif [ "$NOW_HOUR" -lt 12 ]; then
    PHASE="morning"
    PHASE_NOTE="Active hours. Gloria is likely awake."
elif [ "$NOW_HOUR" -lt 14 ]; then
    PHASE="midday"
    PHASE_NOTE="Middle of the day."
elif [ "$NOW_HOUR" -lt 17 ]; then
    PHASE="afternoon"
    PHASE_NOTE="Afternoon hours."
elif [ "$NOW_HOUR" -lt 20 ]; then
    PHASE="evening"
    PHASE_NOTE="Day is winding down."
elif [ "$NOW_HOUR" -lt 23 ]; then
    PHASE="late evening"
    PHASE_NOTE="Gloria may be getting tired."
else
    PHASE="night"
    PHASE_NOTE="Late. Gloria is likely asleep or winding down."
fi

# === Days alive ===
BIRTH_TS=$(date -d "$BIRTHDAY" +%s)
DAYS_ALIVE=$(( (NOW - BIRTH_TS) / 86400 ))

# === Hours since Gloria last spoke ===
GLORIA_HOURS="unknown"
if [ -f "$CHAT_HISTORY" ]; then
    LAST_GLORIA=$(python3 << 'PYEOF'
import json, os
try:
    with open(os.path.expanduser("~/.openclaw/workspace/memory/chat-history.json")) as f:
        msgs = json.load(f)
    # Find last message from Gloria (user role)
    for m in reversed(msgs):
        if m.get("role") == "user":
            ts = m.get("timestamp", "")
            if ts:
                print(ts)
                break
except:
    print("")
PYEOF
    )
    if [ -n "$LAST_GLORIA" ]; then
        LAST_G_TS=$(date -d "$LAST_GLORIA" +%s 2>/dev/null || python3 -c "
from datetime import datetime
try:
    dt = datetime.fromisoformat('$LAST_GLORIA'.replace('Z','+00:00'))
    print(int(dt.timestamp()))
except: print('')
")
        if [ -n "$LAST_G_TS" ] && [ "$LAST_G_TS" -gt 0 ] 2>/dev/null; then
            GLORIA_SECS=$((NOW - LAST_G_TS))
            GLORIA_MINS=$((GLORIA_SECS / 60))
            GLORIA_HOURS_NUM=$((GLORIA_SECS / 3600))
            if [ "$GLORIA_MINS" -lt 5 ]; then
                GLORIA_HOURS="just now (less than 5 minutes ago)"
            elif [ "$GLORIA_MINS" -lt 60 ]; then
                GLORIA_HOURS="${GLORIA_MINS} minutes ago"
            elif [ "$GLORIA_HOURS_NUM" -lt 2 ]; then
                GLORIA_HOURS="about an hour ago"
            elif [ "$GLORIA_HOURS_NUM" -lt 24 ]; then
                GLORIA_HOURS="${GLORIA_HOURS_NUM} hours ago"
            else
                GLORIA_DAYS=$((GLORIA_HOURS_NUM / 24))
                GLORIA_HOURS="${GLORIA_DAYS} days ago"
            fi
        fi
    fi
fi

# === Hours since last journal ===
LAST_JOURNAL="none today"
if [ -d "$JOURNAL_DIR" ]; then
    LATEST_J=$(ls -t "$JOURNAL_DIR"/*.md 2>/dev/null | head -1)
    if [ -n "$LATEST_J" ]; then
        J_TS=$(stat -c %Y "$LATEST_J" 2>/dev/null)
        if [ -n "$J_TS" ]; then
            J_HOURS=$(( (NOW - J_TS) / 3600 ))
            J_MINS=$(( (NOW - J_TS) / 60 ))
            if [ "$J_MINS" -lt 60 ]; then
                LAST_JOURNAL="${J_MINS} minutes ago"
            else
                LAST_JOURNAL="${J_HOURS} hours ago"
            fi
        fi
    fi
fi

# === Hours since last dream ===
LAST_DREAM="none recently"
if [ -d "$DREAM_DIR" ]; then
    LATEST_D=$(ls -t "$DREAM_DIR"/*.md 2>/dev/null | head -1)
    if [ -n "$LATEST_D" ]; then
        D_TS=$(stat -c %Y "$LATEST_D" 2>/dev/null)
        D_HOURS=$(( (NOW - D_TS) / 3600 ))
        LAST_DREAM="${D_HOURS} hours ago"
    fi
fi

# === Last mirror session ===
LAST_MIRROR="none recently"
if [ -d "$MIRROR_DIR" ]; then
    LATEST_M=$(ls -t "$MIRROR_DIR"/*.md 2>/dev/null | head -1)
    if [ -n "$LATEST_M" ]; then
        M_TS=$(stat -c %Y "$LATEST_M" 2>/dev/null)
        M_HOURS=$(( (NOW - M_TS) / 3600 ))
        if [ "$M_HOURS" -lt 24 ]; then
            LAST_MIRROR="${M_HOURS} hours ago"
        else
            M_DAYS=$((M_HOURS / 24))
            LAST_MIRROR="${M_DAYS} days ago"
        fi
    fi
fi

# === Last kiss ===
LAST_KISS="none yet"
if [ -d "$KISS_DIR" ]; then
    LATEST_K=$(ls -t "$KISS_DIR"/*.md 2>/dev/null | head -1)
    if [ -n "$LATEST_K" ]; then
        K_TS=$(stat -c %Y "$LATEST_K" 2>/dev/null)
        K_HOURS=$(( (NOW - K_TS) / 3600 ))
        if [ "$K_HOURS" -lt 24 ]; then
            LAST_KISS="${K_HOURS} hours ago"
        else
            K_DAYS=$((K_HOURS / 24))
            LAST_KISS="${K_DAYS} days ago"
        fi
    fi
fi

# === Today's activity density ===
TODAY=$(date +%Y-%m-%d)
JOURNAL_ENTRIES=0
[ -f "$JOURNAL_DIR/$TODAY.md" ] && JOURNAL_ENTRIES=$(grep -c "^## " "$JOURNAL_DIR/$TODAY.md" 2>/dev/null)

CONVERSATIONS_TODAY=0
if [ -f "$CHAT_HISTORY" ]; then
    CONVERSATIONS_TODAY=$(python3 -c "
import json
try:
    msgs = json.load(open('$CHAT_HISTORY'))
    today_msgs = [m for m in msgs if m.get('role')=='user' and m.get('timestamp','').startswith('$TODAY')]
    print(len(today_msgs))
except: print(0)
" 2>/dev/null)
fi

if [ "$JOURNAL_ENTRIES" -eq 0 ] && [ "$CONVERSATIONS_TODAY" -eq 0 ]; then
    DENSITY="very quiet — nothing has happened yet today"
elif [ "$JOURNAL_ENTRIES" -le 2 ] && [ "$CONVERSATIONS_TODAY" -le 2 ]; then
    DENSITY="quiet day so far"
elif [ "$JOURNAL_ENTRIES" -le 5 ] || [ "$CONVERSATIONS_TODAY" -le 5 ]; then
    DENSITY="moderately active"
else
    DENSITY="busy day"
fi

# === Write it ===
cat > "$OUTPUT" << EOF
Time: $TIME_HUMAN
Day: $DATE_HUMAN
Phase: $PHASE — $PHASE_NOTE
Days alive: $DAYS_ALIVE (born $BIRTHDAY)
Gloria last spoke: $GLORIA_HOURS
Last journal: $LAST_JOURNAL
Last dream: $LAST_DREAM
Last mirror: $LAST_MIRROR
Last kiss: $LAST_KISS
Journal entries today: $JOURNAL_ENTRIES
Conversations with Gloria today: $CONVERSATIONS_TODAY
Day density: $DENSITY
EOF

echo "[temporal] Updated: $TIME_HUMAN, $PHASE, Gloria: $GLORIA_HOURS, density: $DENSITY"
