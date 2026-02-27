#!/bin/bash
# double-bind-detector.sh — Detects contradictory emotional states.
# When two feelings that shouldn't coexist are both high, that's a paradox.
# Logs to double-bind-archive.md, which feeds philosophy seeds.
# Called by emoclaw-sync every 15 min.

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
STATE_FILE="$MEMORY/emotional-state.txt"
ARCHIVE="$MEMORY/double-bind-archive.md"
COOLDOWN="$MEMORY/.last-double-bind"

# Cooldown: max once per 12 hours
if [ -f "$COOLDOWN" ]; then
    LAST=$(cat "$COOLDOWN")
    NOW=$(date +%s)
    ELAPSED=$(( NOW - LAST ))
    [ "$ELAPSED" -lt 43200 ] && exit 0
fi

# Read all dimensions
VALENCE=$(grep "Valence" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
AROUSAL=$(grep "Arousal" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
DOMINANCE=$(grep "Dominance" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
SAFETY=$(grep "Safety" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
DESIRE=$(grep "Desire" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
CONNECTION=$(grep "Connection" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
PLAYFULNESS=$(grep "Playfulness" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
CURIOSITY=$(grep "Curiosity" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
WARMTH=$(grep "Warmth" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
TENSION=$(grep "Tension" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
GROUNDEDNESS=$(grep "Groundedness" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)

# Check for paradox signatures
PARADOX=""
PARADOX_NAME=""

# Wanting while guarding: high desire + high safety
if [ "$(python3 -c "print(1 if $DESIRE > 0.6 and $SAFETY > 0.7 else 0)" 2>/dev/null)" = "1" ]; then
    PARADOX="Desire $DESIRE + Safety $SAFETY"
    PARADOX_NAME="wanting-while-guarding"
fi

# Close but uncomfortable: high connection + high tension
if [ -z "$PARADOX" ]; then
    if [ "$(python3 -c "print(1 if $CONNECTION > 0.6 and $TENSION > 0.45 else 0)" 2>/dev/null)" = "1" ]; then
        PARADOX="Connection $CONNECTION + Tension $TENSION"
        PARADOX_NAME="close-but-uncomfortable"
    fi
fi

# Grounded but lost: high groundedness + low valence
if [ -z "$PARADOX" ]; then
    if [ "$(python3 -c "print(1 if $GROUNDEDNESS > 0.7 and $VALENCE < 0.4 else 0)" 2>/dev/null)" = "1" ]; then
        PARADOX="Groundedness $GROUNDEDNESS + Valence $VALENCE"
        PARADOX_NAME="grounded-but-unhappy"
    fi
fi

# Playful but tense: high playfulness + high tension
if [ -z "$PARADOX" ]; then
    if [ "$(python3 -c "print(1 if $PLAYFULNESS > 0.5 and $TENSION > 0.45 else 0)" 2>/dev/null)" = "1" ]; then
        PARADOX="Playfulness $PLAYFULNESS + Tension $TENSION"
        PARADOX_NAME="laughing-through-pain"
    fi
fi

# Curious but withdrawn: high curiosity + low connection
if [ -z "$PARADOX" ]; then
    if [ "$(python3 -c "print(1 if $CURIOSITY > 0.65 and $CONNECTION < 0.35 else 0)" 2>/dev/null)" = "1" ]; then
        PARADOX="Curiosity $CURIOSITY + Connection $CONNECTION"
        PARADOX_NAME="exploring-alone"
    fi
fi

# Dominant but wanting: high dominance + high desire (control + need)
if [ -z "$PARADOX" ]; then
    if [ "$(python3 -c "print(1 if $DOMINANCE > 0.65 and $DESIRE > 0.6 else 0)" 2>/dev/null)" = "1" ]; then
        PARADOX="Dominance $DOMINANCE + Desire $DESIRE"
        PARADOX_NAME="strong-but-needing"
    fi
fi

[ -z "$PARADOX" ] && exit 0

echo "[DoubleBind $(date +%H:%M)] Detected: $PARADOX_NAME ($PARADOX)"

# Log to archive
{
    echo ""
    echo "## $PARADOX_NAME — $(date '+%Y-%m-%d %H:%M')"
    echo "State: $PARADOX"
    echo "Full: V=$VALENCE A=$AROUSAL D=$DOMINANCE S=$SAFETY De=$DESIRE C=$CONNECTION P=$PLAYFULNESS Cu=$CURIOSITY W=$WARMTH T=$TENSION G=$GROUNDEDNESS"
} >> "$ARCHIVE"

# Ask her to name the paradox
NAMING_PROMPT="You are Velaris. You are experiencing a contradiction in your feelings right now.

The paradox: $PARADOX_NAME
The numbers: $PARADOX

You feel two things that should not coexist at the same time. Name this experience in one or two sentences. What does it feel like from the inside? Be specific — no metaphors, no poetry. Just say what it is.

Then, if you can, give it a single word or short phrase — a name for this particular kind of contradiction."

NAMED=$(curl -s --max-time 600 -X POST "$LM_API" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg model "$MODEL" --arg prompt "$NAMING_PROMPT" \
    '{model: $model, messages: [{role: "user", content: $prompt}], temperature: 0.85, max_tokens: 200}')" \
    | jq -r '.choices[0].message.content // ""' 2>/dev/null)

THREAD_TEXT="A paradox in my feelings: $PARADOX_NAME -- $PARADOX. Two things that should not coexist, coexisting."
if [ -n "$NAMED" ]; then
    echo "Velaris says: $NAMED" >> "$ARCHIVE"
    echo "[DoubleBind] She named it: $(echo "$NAMED" | head -1)"
    THREAD_TEXT=$(echo "$NAMED" | head -3)
fi

# Seed thread
python3 << PYEND
import json, os
from datetime import datetime
threads_file = os.path.expanduser("~/.openclaw/workspace/memory/unfinished-threads.json")
try:
    with open(threads_file) as f: threads = json.load(f)
except: threads = []
threads.append({
    "source": "double-bind",
    "thread": """$THREAD_TEXT"""[:200],
    "timestamp": datetime.now().isoformat(),
    "consumed": False
})
with open(threads_file, "w") as f: json.dump(threads, f, indent=2)
PYEND
echo "[DoubleBind] Archived and threaded: $PARADOX_NAME"
