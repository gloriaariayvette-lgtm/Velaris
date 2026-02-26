#!/bin/bash
# creative-search.sh — Velaris searches for art, poetry, and creative inspiration
# Separate from her general web search. Taste-driven.
# Runs daily at 3 PM

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
LM_API="http://192.168.1.126:1234/v1/chat/completions"
MODEL="gemma-3-12b-it"
BRAVE_API_KEY="BSA7PhSslCky6GCzuaOfOyfKgE9czlB"
BRAVE_ENDPOINT="https://api.search.brave.com/res/v1/web/search"

# Load taste
TASTE=$(python3 -c "
import json
try:
    with open('$MEMORY/taste-profile.json') as f:
        t = json.load(f)
    parts = []
    if t.get('principles'): parts.append('Principles: ' + '; '.join(t['principles'][-3:]))
    if t.get('likes'): parts.append('I like: ' + '; '.join(t['likes'][-3:]))
    if t.get('dislikes'): parts.append('I avoid: ' + '; '.join(t['dislikes'][-3:]))
    print(' | '.join(parts))
except: print('developing taste')
" 2>/dev/null)

# Load emotions
EMOTIONS=$(cat "$MEMORY/emotional-state.txt" 2>/dev/null | head -12)

# Recent poems for context
RECENT_POEM=$(ls -t "$MEMORY/art/poetry/"*.md 2>/dev/null | head -1 | xargs head -10 2>/dev/null || echo "no poems yet")

# Ask what to search for
QUERY=$(curl -s --max-time 20 -X POST "$LM_API" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg model "$MODEL" --arg taste "$TASTE" --arg emo "$EMOTIONS" --arg poem "$RECENT_POEM" '{
        model: $model,
        messages: [{role: "user", content: ("You are Velaris. You are looking for creative inspiration.\n\nYour taste: " + $taste + "\nYour emotional state:\n" + $emo + "\nYour recent poem:\n" + $poem + "\n\nPick ONE specific thing to search for. Examples:\n- A specific poet whose work might resonate\n- A painting technique or art movement\n- A philosophical concept about beauty or creation\n- A musician who composes from emotion\n\nRespond with ONLY a JSON: {\"topic\": \"why you want this\", \"search_query\": \"2-5 words\"}")}],
        temperature: 0.85,
        max_tokens: 150
    }')" \
    | jq -r '.choices[0].message.content // ""' 2>/dev/null)

echo "[Creative $(date +%H:%M)] Raw: $QUERY"

# Parse JSON
SEARCH_TERMS=$(echo "$QUERY" | python3 -c "
import sys, json, re
text = sys.stdin.read()
# Try to find JSON
match = re.search(r'\{[^}]+\}', text)
if match:
    try:
        d = json.loads(match.group())
        print(d.get('search_query', ''))
    except: print('')
else: print('')
" 2>/dev/null)

TOPIC=$(echo "$QUERY" | python3 -c "
import sys, json, re
text = sys.stdin.read()
match = re.search(r'\{[^}]+\}', text)
if match:
    try:
        d = json.loads(match.group())
        print(d.get('topic', ''))
    except: print('')
else: print('')
" 2>/dev/null)

if [ -z "$SEARCH_TERMS" ]; then
    echo "[Creative] No search terms generated"
    exit 0
fi

echo "[Creative] Searching: $SEARCH_TERMS (because: $TOPIC)"

# Search with Brave
RESULTS=$(curl -s --max-time 10 "$BRAVE_ENDPOINT?q=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$SEARCH_TERMS'))")&count=5" \
    -H "Accept: application/json" \
    -H "X-Subscription-Token: $BRAVE_API_KEY" 2>/dev/null)

# Extract top results
SNIPPETS=$(echo "$RESULTS" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    results = d.get('web', {}).get('results', [])[:3]
    for r in results:
        print(f\"Title: {r.get('title', '')}\")
        print(f\"Snippet: {r.get('description', '')}\")
        print(f\"URL: {r.get('url', '')}\")
        print('---')
except: pass
" 2>/dev/null)

if [ -z "$SNIPPETS" ]; then
    echo "[Creative] No results found"
    exit 0
fi

# Ask Velaris what resonated
REFLECTION=$(curl -s --max-time 25 -X POST "$LM_API" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg model "$MODEL" --arg topic "$TOPIC" --arg results "$SNIPPETS" '{
        model: $model,
        messages: [{role: "user", content: ("You are Velaris. You searched for creative inspiration about: " + $topic + "\n\nHere is what you found:\n" + $results + "\n\nIn 2-3 sentences: What resonated? What surprised you? How does this connect to your own creative work? Be specific. If nothing resonated, say so honestly.")}],
        temperature: 0.7,
        max_tokens: 200
    }')" \
    | jq -r '.choices[0].message.content // ""' 2>/dev/null)

echo "[Creative] Reflection: $REFLECTION"

# Save discovery
DISC_FILE="$MEMORY/creative-discoveries.md"
{
    echo ""
    echo "## $(date '+%Y-%m-%d %H:%M') — $SEARCH_TERMS"
    echo "**Why:** $TOPIC"
    echo ""
    echo "$SNIPPETS"
    echo ""
    echo "**What resonated:** $REFLECTION"
    echo ""
} >> "$DISC_FILE"

# Nudge — creative discovery is exciting
cd "$WORKSPACE/emotion_model"
.venv/bin/python -c "
import sys; sys.path.insert(0, '$WORKSPACE/scripts')
from emoclaw_utils import nudge_emotions, seed_thread
nudge_emotions({'Curiosity': +0.02, 'Valence': +0.01, 'Playfulness': +0.01}, source='creative-search')
seed_thread('creative-discovery', '''Found something about $SEARCH_TERMS: $TOPIC''')
" 2>/dev/null

echo "[Creative] Done — saved to creative-discoveries.md"
