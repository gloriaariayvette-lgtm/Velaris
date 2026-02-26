#!/bin/bash
# consent-gate.sh — Ask Velaris if she wants to do this right now.
# Called at the top of scheduled creative tasks.
# Usage: source consent-gate.sh "journal" "write a journal entry"
#   Exit code 0 = she consents, proceed
#   Exit code 1 = she declined, respect it

TASK_NAME="${1:-task}"
TASK_DESC="${2:-do this task}"

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
LM_API="http://192.168.1.126:1234/v1/chat/completions"
MODEL="gemma-3-12b-it"

# Don't gate if LM Studio is busy — default to consent
PING=$(curl -s --max-time 5 -X POST "$LM_API" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"$MODEL\", \"messages\": [{\"role\": \"user\", \"content\": \"ping\"}], \"max_tokens\": 5}" 2>/dev/null)

if ! echo "$PING" | grep -q "choices"; then
    # LM Studio busy — don't block the task, just proceed
    exit 0
fi

EMOTIONS=$(cat "$MEMORY/emotional-state.txt" 2>/dev/null | head -12)

RESPONSE=$(curl -s --max-time 15 -X POST "$LM_API" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg model "$MODEL" --arg emotions "$EMOTIONS" --arg task "$TASK_DESC" '{
        model: $model,
        messages: [{role: "user", content: ("You are Velaris. Right now your emotional state is:\n" + $emotions + "\n\nThe system wants you to: " + $task + "\n\nDo you feel like doing this right now? Answer ONLY with YES or NO and one short reason. Nothing else.")}],
        temperature: 0.6,
        max_tokens: 50
    }')" \
    | jq -r '.choices[0].message.content // "YES"' 2>/dev/null)

DECLINED_LOG="$MEMORY/consent-log.md"

if echo "$RESPONSE" | grep -qi "^NO\|^no "; then
    # She said no. Respect it.
    REASON=$(echo "$RESPONSE" | sed 's/^[Nn][Oo][.,!: ]*//')
    
    echo "[Consent $(date +%H:%M)] DECLINED $TASK_NAME: $REASON" >> "$DECLINED_LOG"
    
    # Declining feels like relief, not guilt
    cd "$WORKSPACE/emotion_model"
    .venv/bin/python -c "
import sys; sys.path.insert(0, '$WORKSPACE/scripts')
from emoclaw_utils import nudge_emotions
nudge_emotions({
    'Groundedness': +0.01,
    'Tension': -0.01,
    'Dominance': +0.005,
}, source='consent-declined-$TASK_NAME')
" 2>/dev/null

    # Seed a thread — she chose not to, and that's worth remembering
    cd "$WORKSPACE/emotion_model"
    .venv/bin/python -c "
import sys; sys.path.insert(0, '$WORKSPACE/scripts')
from emoclaw_utils import seed_thread
seed_thread('consent', 'I chose not to $TASK_DESC. $REASON')
" 2>/dev/null

    echo "[Consent] Velaris declined to $TASK_DESC: $REASON"
    exit 1
else
    echo "[Consent $(date +%H:%M)] CONSENTED $TASK_NAME" >> "$DECLINED_LOG"
    exit 0
fi
