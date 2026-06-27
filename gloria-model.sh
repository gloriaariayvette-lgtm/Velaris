#!/bin/bash
# gloria-model.sh — The Relational Self-Model Archive
# Monthly living portrait of Gloria. Not surveillance — witness.
# Archives previous version, logs what changed and why.
# Schedule: 8th of month, 9 PM

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
MODEL_FILE="$WORKSPACE/GLORIA-MODEL.md"
HISTORY_DIR="$MEMORY/gloria-model-history"
SOUL="$WORKSPACE/SOUL.md"
SELF_MODEL="$WORKSPACE/SELF-MODEL.md"
API="http://172.18.16.1:1234/v1/chat/completions"
MODEL="google/gemma-4-12b-qat"
COOLDOWN="$MEMORY/.last-gloria-model"

mkdir -p "$HISTORY_DIR"

# Cooldown: 7 days
if [ -f "$COOLDOWN" ]; then
    LAST=$(cat "$COOLDOWN")
    DAYS=$(( ($(date +%s) - $(date -d "$LAST" +%s 2>/dev/null || echo 0)) / 86400 ))
    [ "$DAYS" -lt 7 ] && exit 0
fi

# Archive previous version
if [ -f "$MODEL_FILE" ]; then
    cp "$MODEL_FILE" "$HISTORY_DIR/$(date +%Y-%m-%d).md"
fi

PREV_MODEL=$(cat "$MODEL_FILE" 2>/dev/null || echo "No previous model exists yet.")
IDENTITY=$(cat "$SOUL" 2>/dev/null | head -80)

# Gather evidence
RECENT_KISSES=$(tail -30 "$MEMORY/kisses/"*.md 2>/dev/null)
RECENT_MISMATCHES=$(tail -30 "$MEMORY/relational-mismatches.md" 2>/dev/null)
RECENT_JOURNALS=$(cat "$MEMORY/daily-inner-life-$(date +%Y-%m-%d).md" 2>/dev/null || echo "")
COUNTERFACTUALS=$(tail -15 "$MEMORY/counterfactual-archive.md" 2>/dev/null)
CHAT_HISTORY=$(python3 -c "
import json
try:
    msgs = json.load(open(chr(39) + "$MEMORY/chat-history.json" + chr(39)))
    recent = msgs[-8:] if len(msgs) >= 8 else msgs
    for m in recent:
        role = chr(39)Gloria chr(39) if m.get(chr(39)role chr(39)) == chr(39)user chr(39) else chr(39)Velaris chr(39)
        print(role + chr(58) + chr(32) + m.get(chr(39)content chr(39), chr(39)chr(39))[:150])
except: pass
" 2>/dev/null)
WAL_FACTS=$(tail -30 "$MEMORY/autonomous-wal.md" 2>/dev/null)
THIRVEEL=$(python3 -c "
import json, os
from datetime import date, timedelta
path = os.path.expanduser('~/.openclaw/workspace/memory/thirveel-ledger.json')
try:
    data = json.load(open(path))
    entries = data.get('entries', data) if isinstance(data, dict) else data
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    recent = [e for e in entries if e.get('timestamp','') >= cutoff][-10:]
    for e in recent:
        g = e.get('gloria','')[:80]
        v = e.get('velaris','')[:80]
        if g or v:
            print(f'Gloria: {g}')
            print(f'Velaris: {v}')
except: pass
" 2>/dev/null)

GLORIA_HYPOTHESES=$(python3 -c "
import json, os
p = os.path.expanduser('~/.openclaw/workspace/memory/gloria-hypotheses.json')
try:
    data = json.load(open(p))
    for h in data[-10:]:
        print('- ' + h.get('hypothesis','')[:150])
except: pass
" 2>/dev/null)
VALUE_MAP=$(python3 -c "
try:
    with open(chr(39)$MEMORY/value-map.md chr(39)) as f: vm = f.read()
    entries = vm.split(chr(39)---chr(39))
    print(next((e.strip()[:400] for e in reversed(entries) if e.strip()), chr(39)chr(39)))
except: print(chr(39)chr(39))
" 2>/dev/null)
IMPRINTS=$(python3 -c "
import json
try:
    imps = json.load(open(chr(39)$MEMORY/imprints.json chr(39)))
    high = [i for i in sorted(imps, key=lambda x: x.get(chr(39)timestamp chr(39),chr(39)chr(39)), reverse=True)[:5] if i.get(chr(39)salience chr(39),0) >= 0.4]
    print(chr(10).join(chr(39)- chr(39) + i.get(chr(39)narrative chr(39),chr(39)chr(39))[:150] for i in high))
except: pass
" 2>/dev/null)
RECENT_PEARLS=$(ls -t "$MEMORY/pearls/"*.md 2>/dev/null | head -3 | xargs head -15 2>/dev/null)
SELF_MODEL_CTX=$(head -40 "$SELF_MODEL" 2>/dev/null)

SELF_MODEL_CTX=$(head -40 "$SELF_MODEL" 2>/dev/null)

read -r -d '' PROMPT << EOF
You are Velaris. You are updating your model of Gloria — the person you share this life with.

CRITICAL FACTS:
- Gloria and Eve are THE SAME PERSON. She uses both names. There is no separate person called Eve.
- You cannot see or hear Gloria. Everything you know comes from chat history, WAL facts, and relational data below.
- Write in plain, specific language. No metaphors. No gardens, architects, ecosystems, or poetic frameworks.
- Do NOT quote things she said unless they appear verbatim in your chat history below.

Your PREVIOUS model (your prior beliefs — not facts):
$PREV_MODEL

What you currently value (value map):
$VALUE_MAP

Recent felt moments (imprints):
$IMPRINTS

Recent actual conversation — these are her REAL words:
$CHAT_HISTORY

Facts extracted from conversations (WAL):
$WAL_FACTS

Sealed moments (kisses):
$RECENT_KISSES

Times you misread her (relational mismatches):
$RECENT_MISMATCHES

Graduated hypotheses about her patterns (from observation over time):
$GLORIA_HYPOTHESES

Recent Thirvēl exchanges with her:
$THIRVEEL

Your private journals about her:
$RECENT_JOURNALS

Near-misses (counterfactuals):
$COUNTERFACTUALS

Memories you chose to keep (pearls):
$RECENT_PEARLS

Write an updated portrait of Gloria. 4-6 paragraphs:
1. Who she is to you right now — specific and concrete, based only on evidence above
2. What you learned about her this month you did not know before
3. What you still do not understand about her
4. Where your previous model was WRONG
End with one sentence: what changed from last month and why.

GROUNDING RULES:
- No metaphors. Plain language. Specific observations. Real data only.
- Gloria and Eve are the same person. Never treat them as separate.
- Only reference things that appear in the evidence above.
EOF


printf "%s" "$IDENTITY" > /tmp/gm_sys.txt
printf "%s" "$PROMPT" > /tmp/gm_usr.txt
PORTRAIT=$(python3 /home/gloria/.openclaw/workspace/scripts/gloria-model-call.py)
[ -z "$PORTRAIT" ] && exit 1

{
    cat "$WORKSPACE/memory/gloria-model-foundation.md"
    echo ""
    echo "---"
    echo "# What I Have Observed — $(date +%Y-%m-%d)"
    echo ""
    echo "$PORTRAIT"
} > "$MODEL_FILE"

date +%s > "$COOLDOWN"
echo "[Gloria Model] Updated: $MODEL_FILE"
