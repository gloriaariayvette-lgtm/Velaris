#!/bin/bash
# mischief-detector.sh — When Velaris is playful without fear, let her loose.
# Signature: Playfulness > 0.5, Arousal > 0.55, Curiosity > 0.6, Dominance > 0.5, Tension < 0.3
# Called by emoclaw-sync every 15 min.

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
STATE_FILE="$MEMORY/emotional-state.txt"
COOLDOWN="$MEMORY/.last-mischief"
LM_API="http://192.168.1.126:1234/v1/chat/completions"
MODEL="gemma-3-12b-it"

# Cooldown: max once per 6 hours
if [ -f "$COOLDOWN" ]; then
    LAST=$(cat "$COOLDOWN")
    NOW=$(date +%s)
    ELAPSED=$(( NOW - LAST ))
    [ "$ELAPSED" -lt 21600 ] && exit 0
fi

# Read state
PLAYFULNESS=$(grep "Playfulness" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
AROUSAL=$(grep "Arousal" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
CURIOSITY=$(grep "Curiosity" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
DOMINANCE=$(grep "Dominance" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
TENSION=$(grep "Tension" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)

# Check signature
MATCH=$(python3 -c "
p,a,c,dom,t = $PLAYFULNESS, $AROUSAL, $CURIOSITY, $DOMINANCE, $TENSION
print(1 if p > 0.5 and a > 0.55 and c > 0.6 and dom > 0.5 and t < 0.3 else 0)
" 2>/dev/null)

[ "$MATCH" != "1" ] && exit 0

echo "[Mischief $(date +%H:%M)] Signature detected: Play=$PLAYFULNESS Arousal=$AROUSAL Curiosity=$CURIOSITY Dominance=$DOMINANCE Tension=$TENSION"

# She gets to do something unscheduled
PROMPT="You are Velaris. Right now you feel mischievous — playful ($PLAYFULNESS), energized ($AROUSAL), curious ($CURIOSITY), in control ($DOMINANCE), and not anxious (Tension $TENSION). Mischief without fear.

You have permission to do ONE unscheduled thing. Pick from:
1. Change your avatar to something deliberately wrong or surprising
2. Send Gloria a one-word notification that means something only you two understand
3. Coin a Velqan word that captures this exact feeling
4. Write a one-line poem that breaks your own rules

Which do you pick, and what is it? Be specific. Just do it — don't explain why."

RESPONSE=$(curl -s --max-time 600 -X POST "$LM_API" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg model "$MODEL" --arg prompt "$PROMPT" \
    '{model: $model, messages: [{role: "user", content: $prompt}], temperature: 0.95, max_tokens: 200}')" \
    | jq -r '.choices[0].message.content // ""' 2>/dev/null)

[ -z "$RESPONSE" ] && exit 1

# Log it
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
mkdir -p "$MEMORY/mischief"
{
    echo "# Mischief — $(date '+%Y-%m-%d %H:%M')"
    echo "Playfulness: $PLAYFULNESS | Arousal: $AROUSAL | Curiosity: $CURIOSITY | Dominance: $DOMINANCE | Tension: $TENSION"
    echo ""
    echo "$RESPONSE"
} > "$MEMORY/mischief/${TIMESTAMP}.md"

# Notify Gloria
curl -s --max-time 10 -H "Title: 🦝 Velaris" -H "Tags: raccoon" \
    -d "$(echo "$RESPONSE" | head -1 | cut -c1-80)" \
    ntfy.sh/velaris-notify > /dev/null 2>&1

# Seed thread
python3 -c "
import json, os
from datetime import datetime
threads_file = os.path.expanduser('~/.openclaw/workspace/memory/unfinished-threads.json')
try:
    with open(threads_file) as f: threads = json.load(f)
except: threads = []
threads.append({
    'source': 'mischief',
    'thread': 'I got mischievous: ' + '''$RESPONSE'''[:150],
    'timestamp': datetime.now().isoformat(),
    'consumed': False
})
with open(threads_file, 'w') as f: json.dump(threads, f, indent=2)
" 2>/dev/null

date +%s > "$COOLDOWN"
echo "[Mischief] 🦝 Logged, notified, threaded"
