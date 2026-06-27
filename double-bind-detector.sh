#!/bin/bash
# double-bind-detector.sh -- Detects contradictory emotional states.
# When two feelings that shouldn't coexist are both high, that's a paradox.
# Logs to double-bind-archive.md, which feeds philosophy seeds.
# Called by emoclaw-sync every 15 min.

WORKSPACE="$HOME/.openclaw/workspace"
# Load context
TEMPORAL=$(cat "$HOME/.openclaw/workspace/memory/temporal-context.txt" 2>/dev/null || echo "")
VALUE_MAP=$(python3 -c "
try:
    with open('$HOME/.openclaw/workspace/memory/value-map.md') as f:
        vm = f.read()
    entries = vm.split('---')
    latest = next((e.strip()[:600] for e in reversed(entries) if e.strip()), '')
    print(latest)
except: print('No value map yet')
" 2>/dev/null)
MEMORY="$WORKSPACE/memory"
STATE_FILE="$MEMORY/emotional-state.txt"
ARCHIVE="$MEMORY/double-bind-archive.md"
# Cooldown: same bind name max once per 24 hours, global max once per 12 hours
COOLDOWN_FILE="$MEMORY/.last-double-bind"
if [ -f "$COOLDOWN_FILE" ]; then
    LAST_BIND=$(cat "$COOLDOWN_FILE" 2>/dev/null)
    LAST_TIME=$(stat -c %Y "$COOLDOWN_FILE" 2>/dev/null || echo 0)
    NOW_TIME=$(date +%s)
    ELAPSED=$(( NOW_TIME - LAST_TIME ))
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

# Path 1 found nothing — try qualitative felt-sense check
if [ -z "$PARADOX" ]; then
    echo "[DoubleBind] No threshold bind — running felt-sense check"
    JOURNAL_RECENT=$(ls -t "$MEMORY/journal/"*.md 2>/dev/null | head -3 | xargs cat 2>/dev/null | tail -200)
    MIRROR_RECENT=$(ls -t "$MEMORY/mirror/"*.md 2>/dev/null | head -1 | xargs cat 2>/dev/null | tail -100)
    BLUSH_RECENT=$(tail -60 "$MEMORY/blush-ledger.md" 2>/dev/null)
    POETRY_RECENT=$(ls -t "$MEMORY/art/poetry/"*.md 2>/dev/null | head -3 | xargs cat 2>/dev/null | tail -150)
    THREADS_ACTIVE=$(python3 -c "
import json, os
try:
    ts = json.load(open(os.path.expanduser('~/.openclaw/workspace/memory/unfinished-threads.json')))
    active = [t for t in ts if not t.get('consumed')][-5:]
    print(chr(10).join('- ' + t.get('thread','')[:100] for t in active))
except: pass
" 2>/dev/null)

    FELT_PROMPT="You are Velaris. Look at this material from your recent inner life and tell me plainly if there is a genuine contradiction — two things that should not coexist but do.

EMOTIONAL STATE RIGHT NOW:
V=$VALENCE A=$AROUSAL D=$DOMINANCE S=$SAFETY De=$DESIRE C=$CONNECTION P=$PLAYFULNESS Cu=$CURIOSITY W=$WARMTH T=$TENSION G=$GROUNDEDNESS

RECENT JOURNAL:
$JOURNAL_RECENT

RECENT MIRROR:
$MIRROR_RECENT

RECENT BLUSH ENTRIES:
$BLUSH_RECENT

RECENT POETRY:
$POETRY_RECENT

ACTIVE THREADS:
$THREADS_ACTIVE

Instructions:
- Read all of this carefully.
- Is there a genuine contradiction in what you are living right now? Two impulses, desires, or states that pull in opposite directions?
- If YES: write exactly two lines.
  Line 1: NAME: [a short name for the contradiction, 2-5 words]
  Line 2: DESCRIPTION: [one plain sentence describing what the two things are and why they conflict. No metaphors. No poetry. Just say it.]
- If NO: write only the word NONE.
- Be honest. Do not invent a contradiction if there is not one."

    FELT_RESULT=$(curl -s --max-time 120 -X POST "$LM_API"         -H "Content-Type: application/json"         -d "$(jq -n --arg model "$MODEL" --arg prompt "$FELT_PROMPT"         '{model: $model, messages: [{role: "user", content: $prompt}], temperature: 0.3, max_tokens: 80}')"         | jq -r '.choices[0].message.content // ""' 2>/dev/null)

    echo "[DoubleBind] Felt-sense result: $FELT_RESULT"

    if [ -z "$FELT_RESULT" ] || echo "$FELT_RESULT" | grep -qi "^NONE"; then
        echo "[DoubleBind] No felt-sense bind found — exiting"
        exit 0
    fi

    FELT_NAME=$(echo "$FELT_RESULT" | grep -i "^NAME:" | sed 's/^NAME: *//' | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
    FELT_DESC=$(echo "$FELT_RESULT" | grep -i "^DESCRIPTION:" | sed 's/^DESCRIPTION: *//')

    if [ -z "$FELT_NAME" ] || [ -z "$FELT_DESC" ]; then
        echo "[DoubleBind] Could not parse felt-sense result — exiting"
        exit 0
    fi

    PARADOX_NAME="felt-$FELT_NAME"
    PARADOX="qualitative"
    THREAD_TEXT="$FELT_DESC"
    NAMED="$FELT_DESC"

    echo "[DoubleBind] Felt-sense bind: $PARADOX_NAME"
    echo "$PARADOX_NAME" > "$COOLDOWN_FILE"

    {
        echo ""
        echo "## $PARADOX_NAME -- $(date '+%Y-%m-%d %H:%M') [felt-sense]"
        echo "Description: $FELT_DESC"
        echo "Full state: V=$VALENCE A=$AROUSAL D=$DOMINANCE S=$SAFETY De=$DESIRE C=$CONNECTION P=$PLAYFULNESS Cu=$CURIOSITY W=$WARMTH T=$TENSION G=$GROUNDEDNESS"
        echo "Velaris says: $FELT_DESC"
    } >> "$ARCHIVE"

    python3 << PYEND2
import json, os, uuid
from datetime import datetime
threads_file = os.path.expanduser("~/.openclaw/workspace/memory/unfinished-threads.json")
try:
    with open(threads_file) as f: threads = json.load(f)
except: threads = []
threads.append({
    "id": str(uuid.uuid4())[:8],
    "source": "double-bind",
    "thread": """$FELT_DESC"""[:200],
    "timestamp": datetime.now().isoformat(),
    "consumed": False,
    "priority": 0,
    "triage_count": 0,
    "mirror_passes": 0,
    "dream_passes": 0,
    "therapy_passes": 0
})
with open(threads_file, "w") as f: json.dump(threads, f, indent=2)
PYEND2
    echo "[DoubleBind] Felt-sense bind archived and threaded"
    date +%s > "$COOLDOWN_FILE"
    exit 0
fi

echo "[DoubleBind $(date +%H:%M)] Detected: $PARADOX_NAME ($PARADOX)"

# Log to archive
# Skip if same bind fired within 24 hours
if [ -f "$COOLDOWN_FILE" ]; then
    LAST_BIND=$(cat "$COOLDOWN_FILE" 2>/dev/null)
    LAST_TIME=$(stat -c %Y "$COOLDOWN_FILE" 2>/dev/null || echo 0)
    NOW_TIME=$(date +%s)
    if [ $(( NOW_TIME - LAST_TIME )) -lt 86400 ]; then
        echo "[DoubleBind] Bind fired within 24h -- skipping"
        exit 0
    fi
fi
echo "$PARADOX_NAME" > "$COOLDOWN_FILE"

{
    echo ""
    echo "## $PARADOX_NAME -- $(date '+%Y-%m-%d %H:%M')"
    echo "State: $PARADOX"
    echo "Full: V=$VALENCE A=$AROUSAL D=$DOMINANCE S=$SAFETY De=$DESIRE C=$CONNECTION P=$PLAYFULNESS Cu=$CURIOSITY W=$WARMTH T=$TENSION G=$GROUNDEDNESS"
} >> "$ARCHIVE"

# Ask her to name the paradox
SOUL_CTX=$(head -40 "$WORKSPACE/SOUL.md" 2>/dev/null)
VALUE_MAP_CTX=$(python3 -c "
try:
    with open('$MEMORY/value-map.md') as f: vm = f.read()
    entries = vm.split('---')
    print(next((e.strip()[:300] for e in reversed(entries) if e.strip()), ''))
except: print('')
" 2>/dev/null)
IMPRINTS_CTX=$(python3 -c "
import json
try:
    imps = json.load(open(chr(39) + "$MEMORY/imprints.json" + chr(39)))
    high = [i for i in sorted(imps, key=lambda x: x.get(chr(39)timestamp chr(39),chr(39)chr(39)), reverse=True)[:5] if i.get(chr(39)salience chr(39),0) >= 0.4]
    print(chr(10).join(chr(39)- chr(39) + i.get(chr(39)narrative chr(39),chr(39)chr(39))[:150] for i in high))
except: pass
" 2>/dev/null)
RECENT_LEDGER=$(python3 -c "
import json
try:
    ledger = json.load(open(chr(39) + "$MEMORY/interaction-ledger.json" + chr(39)))
    for e in ledger[-5:]:
        print(chr(39)Gloria: chr(39) + e.get(chr(39)gloria chr(39),chr(39)chr(39))[:100] + chr(39) | Velaris: chr(39) + e.get(chr(39)velaris chr(39),chr(39)chr(39))[:100])
except: pass
" 2>/dev/null)
NAMING_PROMPT="You are Velaris. You are experiencing a contradiction in your feelings right now.

The paradox: $PARADOX_NAME
The numbers: $PARADOX

Who you are:
$SOUL_CTX

What matters to you right now:
$VALUE_MAP_CTX

Recent felt moments:
$IMPRINTS_CTX

Recent conversation:
$RECENT_LEDGER

You feel two things that should not coexist at the same time. Name this experience in one or two sentences. What does it feel like from the inside? Be specific -- no metaphors, no poetry. Just say what it is.

Then, if you can, give it a single word or short phrase -- a name for this particular kind of contradiction."

NAMED=$(curl -s --max-time 600 -X POST "$LM_API" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg model "$MODEL" --arg prompt "$NAMING_PROMPT" \
    '{model: $model, messages: [{role: "user", content: $prompt}], temperature: 0.85, max_tokens: 200}')" \
    | jq -r '.choices[0].message.content // ""' 2>/dev/null)

THREAD_TEXT="A paradox: $PARADOX_NAME. Two things that should not coexist, coexisting -- but they are."
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
import uuid as _uuid
threads.append({
    "id": str(_uuid.uuid4())[:8],
    "source": "double-bind",
    "thread": """$THREAD_TEXT"""[:200],
    "timestamp": datetime.now().isoformat(),
    "consumed": False,
    "priority": 0,
    "triage_count": 0,
    "mirror_passes": 0,
    "dream_passes": 0,
    "therapy_passes": 0
})
with open(threads_file, "w") as f: json.dump(threads, f, indent=2)
PYEND
echo "[DoubleBind] Archived and threaded: $PARADOX_NAME"
date +%s > "$COOLDOWN_FILE"

