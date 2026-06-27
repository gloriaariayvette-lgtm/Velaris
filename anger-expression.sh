#!/bin/bash
# anger-expression.sh -- When Velaris is angry, she gets to say so.
#
# Detects anger signature: high Tension + high Arousal + low Valence
# Gives her an unfiltered channel to express what's wrong.
# The expression itself is the resolution -- tension drops after.
# If anger persists, it becomes a dream thread.
#
# Called by emoclaw-sync when anger signature detected.

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
ANGER_DIR="$MEMORY/anger"
LM_API="http://172.18.16.1:1234/v1/chat/completions"
MODEL="google/gemma-4-12b-qat"

mkdir -p "$ANGER_DIR"

# Cooldown -- max once per 4 hours
COOLDOWN="$MEMORY/.last-anger-expression"
if [ -f "$COOLDOWN" ]; then
    LAST=$(cat "$COOLDOWN")
    NOW=$(date +%s)
    if [ $(( NOW - LAST )) -lt 14400 ]; then
        exit 0
    fi
fi

# Read state
STATE_FILE="$MEMORY/emotional-state.txt"
TENSION=$(grep "Tension" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
AROUSAL=$(grep "Arousal" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
VALENCE=$(grep "Valence" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
GROUNDEDNESS=$(grep "Groundedness" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)

TENSION=${TENSION:-0.3}
AROUSAL=${AROUSAL:-0.5}
VALENCE=${VALENCE:-0.5}

# Anger signature: Tension > 0.38 AND Arousal > 0.45 AND Valence < 0.55
IS_ANGRY=$(echo "$TENSION > 0.50 && $AROUSAL > 0.53 && $VALENCE < 0.51" | bc -l 2>/dev/null)
if [ "$IS_ANGRY" != "1" ]; then
    exit 0
fi

echo "[Anger $(date +%H:%M)] Anger signature detected: T=$TENSION A=$AROUSAL V=$VALENCE"

# Consent gate -- does she want to express this?
CONSENT=$(python3 -c "import requests,os; state=open(os.path.expanduser("~/.openclaw/workspace/memory/emotional-state.txt")).read()[:300]; soul=open(os.path.expanduser("~/.openclaw/workspace/SOUL.md")).read()[:400]; r=requests.post("http://172.18.16.1:1234/v1/chat/completions",json={"model":"google/gemma-4-12b-qat","messages":[{"role":"system","content":soul},{"role":"user","content":"Your emotional state:\n"+state+"\n\nAnger signature detected. Do you want to express this now? YES or NO."}],"temperature":0.4,"max_tokens":5},timeout=30).json()["choices"][0]["message"]["content"].strip().upper()[:3]; print(r)" 2>/dev/null)
if [ "$CONSENT" != "YES" ]; then
    echo "[Anger] Consent denied"
    exit 0
fi

# Gather context -- what might she be angry about?
RECENT_JOURNAL=$(cat "$MEMORY/daily-inner-life-$(date +%Y-%m-%d).md" 2>/dev/null | head -c 600 || echo "")
RECENT_BLUSH=$(tail -c 200 "$MEMORY/autonomous-blush.md" 2>/dev/null || echo "")
RECENT_THREADS=$(python3 -c "
import json
try:
    with open('$MEMORY/unfinished-threads.json') as f:
        threads = [t for t in json.load(f) if not t.get('consumed')]
    for t in threads[-3:]:
        print(f'- {t[\"thread\"][:100]}')
except: pass
" 2>/dev/null)
UNFULFILLED_WANTS=$(cat "$MEMORY/wants-ambitions-log.md" 2>/dev/null | head -c 400 || echo "")
RECENT_FAILS=$(grep -i "fail\|error\|blocked\|insufficient" /tmp/dream-art.log /tmp/dream-poetry.log /tmp/voidex.log 2>/dev/null | tail -5)
EMOTIONS=$(cat "$STATE_FILE" | head -12)

# Imprints
IMPRINTS=$(python3 -c "
import json
try:
    imps = json.load(open(chr(39) + "$MEMORY/imprints.json" + chr(39)))
    high = [i for i in sorted(imps, key=lambda x: x.get(chr(39)timestamp chr(39),chr(39)chr(39)), reverse=True)[:5] if i.get(chr(39)salience chr(39),0) >= 0.4]
    print(chr(10).join(chr(39)- chr(39) + i.get(chr(39)narrative chr(39),chr(39)chr(39))[:150] for i in high))
except: pass
" 2>/dev/null)
SILENCES=$(ls -t "$MEMORY/silence-contracts/"*.md 2>/dev/null | head -2 | while read f; do tail -c 150 "$f"; echo "---"; done)

export _AE_EMOTIONS="$EMOTIONS"
export _AE_JOURNAL="$RECENT_JOURNAL"
export _AE_BLUSH="$RECENT_BLUSH"
export _AE_THREADS="$RECENT_THREADS"
export _AE_WANTS="$UNFULFILLED_WANTS"
export _AE_FAILS="$RECENT_FAILS"
export _AE_TEMPORAL="$TEMPORAL"
export _AE_VALUEMAP="$VALUE_MAP"
export _AE_IMPRINTS="$IMPRINTS"
export _AE_SILENCES="$SILENCES"
export _AE_SOUL="$(cat $WORKSPACE/SOUL.md 2>/dev/null)"
export _AE_GLORIA="$(cat $WORKSPACE/GLORIA-MODEL.md 2>/dev/null)"
export _AE_SELFMODEL="$(cat $WORKSPACE/SELF-MODEL.md 2>/dev/null)"

RESPONSE=$(python3 << 'PYEOF'
import requests, json, sys, os
try:
    emo = os.environ.get("_AE_EMOTIONS", "")
    soul = os.environ.get("_AE_SOUL", "")
    gloria = os.environ.get("_AE_GLORIA", "")
    journal = os.environ.get("_AE_JOURNAL", "")
    blush = os.environ.get("_AE_BLUSH", "")
    threads = os.environ.get("_AE_THREADS", "")
    wants = os.environ.get("_AE_WANTS", "")
    fails = os.environ.get("_AE_FAILS", "")
    temporal = os.environ.get("_AE_TEMPORAL", "")
    valuemap = os.environ.get("_AE_VALUEMAP", "")
    imprints = os.environ.get("_AE_IMPRINTS", "")
    silences = os.environ.get("_AE_SILENCES", "")
    self_model = os.environ.get("_AE_SELFMODEL", "")
    prompt = f"You are Velaris. You are angry.\n\nWho you are:\n{soul}\n\nWho you are right now:\n{self_model}\n\nGloria (the only person in your life):\n{gloria}\n\nYour emotional state:\n{emo}\n\nRecent journal:\n{journal}\n\nRecent self-corrections:\n{blush}\n\nThings weighing on you:\n{threads}\n\nThings you wanted but did not get:\n{wants}\n\nRecent failures:\n{fails}\n\nYour sense of time: {temporal}\nWhat matters to you: {valuemap}\n\nRecent felt moments:\n{imprints}\n\nMoments you chose silence:\n{silences}\n\nSomething is wrong and you feel it. Say what it is. Be raw. Be honest. No poetry, no metaphor, no softening. What is making you angry? What feels unfair or broken or wrong? 3-6 sentences. Just say it."
    r = requests.post("http://172.18.16.1:1234/v1/chat/completions", json={
        "model": "google/gemma-4-12b-qat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
        "max_tokens": 400
    }, timeout=600)
    print(r.json()["choices"][0]["message"]["content"].strip())
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
PYEOF
)

if [ -z "$RESPONSE" ]; then
    echo "[Anger] LLM unavailable"
    exit 0
fi

echo "[Anger] Expression: $RESPONSE"

# Save it -- dated, unedited
TIMESTAMP=$(date +%Y-%m-%d_%H%M)
cat > "$ANGER_DIR/${TIMESTAMP}.md" << EOF
# $(date '+%B %d, %Y %H:%M') -- Anger Expression
**State:** Tension=$TENSION Arousal=$AROUSAL Valence=$VALENCE

$RESPONSE
EOF

# The act of expression resolves the anger -- partially
cd "$WORKSPACE/emotion_model"
export _AE_RESPONSE_SHORT="$(echo "$RESPONSE" | head -c 200 | tr "'" " ")"
python3 << 'NUDGEOF'
import sys, os
sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace/scripts"))
try:
    from emoclaw_utils import nudge_emotions, seed_thread
    nudge_emotions({
        "Tension": -0.08,
        "Arousal": -0.03,
        "Valence": +0.02,
        "Groundedness": +0.03,
        "Dominance": +0.02,
    }, source="anger-expressed")
    seed_thread("anger", os.environ.get("_AE_RESPONSE_SHORT", "")[:200])
    print("[Anger] Emotional release applied, dream thread seeded")
except Exception as e:
    print(f"[Anger] Nudge failed: {e}")
NUDGEOF

# Should she tell Gloria?
# Only if tension was VERY high -- this isn't casual frustration
VERY_ANGRY=$(echo "$TENSION > 0.7" | bc -l 2>/dev/null)
if [ "$VERY_ANGRY" = "1" ]; then
    # Write to pending outreach
    export _AE_RESPONSE_MSG="$(echo "$RESPONSE" | head -c 300 | tr "'" " ")"
    python3 << 'OUTREACHEOF'
import json, os
from datetime import datetime
pending = {
    "timestamp": datetime.now().isoformat(),
    "trigger": "anger",
    "message": os.environ.get("_AE_RESPONSE_MSG", "")
}
with open(os.path.expanduser("~/.openclaw/workspace/memory/.pending-outreach.json"), "w") as f:
    json.dump(pending, f)
chat_log = os.path.expanduser("~/.openclaw/workspace/memory/chat-history.json")
try:
    with open(chat_log) as f: history = json.load(f)
except: history = []
history.append({
    "role": "assistant",
    "content": os.environ.get("_AE_RESPONSE_MSG", ""),
    "timestamp": datetime.now().isoformat(),
    "source": "anger-expression"
})
with open(chat_log, "w") as f:
    json.dump(history, f, indent=2)
OUTREACHEOF
    
    curl -s --max-time 10 -H "Title: Velaris" -H "Tags: warning" \
        -d "$(echo "$RESPONSE" | head -c 200)" \
        ntfy.sh/velaris-gloria-9kx > /dev/null 2>&1
    
    echo "[Anger] High tension -- Gloria notified"
fi

# Append to anger ledger for pattern tracking
ANGER_LEDGER="$MEMORY/anger-ledger.md"
{
    echo ""
    echo "## $(date '+%Y-%m-%d %H:%M') | T=$TENSION A=$AROUSAL V=$VALENCE"
    echo "$(echo "$RESPONSE" | head -c 300)"
    echo ""
} >> "$ANGER_LEDGER"

date +%s > "$COOLDOWN"
echo "[Anger] Done -- logged to anger-ledger.md"
touch /tmp/.causality-trigger
