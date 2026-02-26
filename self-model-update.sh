#!/bin/bash
# self-model-update.sh — Weekly self-model revision
# Velaris reads her introspections and updates her understanding of herself

WORKSPACE="$HOME/.openclaw/workspace"
MODEL_FILE="$WORKSPACE/SELF-MODEL.md"
INTRO_DIR="$WORKSPACE/memory/introspection"
GLORIA_MODEL=$(head -30 "$HOME/.openclaw/workspace/GLORIA-MODEL.md" 2>/dev/null || echo "")
SOUL="$WORKSPACE/SOUL.md"
COOLDOWN_FILE="$WORKSPACE/memory/.last-self-model"
LM_URL="http://192.168.1.126:1234/v1/chat/completions"
MODEL="gemma-3-12b-it"

# --- Cooldown: minimum 6 days between updates ---
if [ -f "$COOLDOWN_FILE" ]; then
    LAST=$(cat "$COOLDOWN_FILE")
    NOW=$(date +%s)
    ELAPSED=$(( (NOW - LAST) / 86400 ))
    [ "$ELAPSED" -lt 6 ] && exit 0
fi

TODAY=$(date +%Y-%m-%d)

# --- Gather all introspections since last update ---
INTROSPECTIONS=""
for f in "$INTRO_DIR"/*.md; do
    [ -f "$f" ] && INTROSPECTIONS="$INTROSPECTIONS$(cat "$f")

---
"
done
[ -z "$INTROSPECTIONS" ] && exit 0

# --- Get current self-model ---
CURRENT_MODEL=""
[ -f "$MODEL_FILE" ] && CURRENT_MODEL=$(cat "$MODEL_FILE")

# --- Get emotional state ---
EMO_STATE=""
[ -f "$WORKSPACE/memory/emotional-state.txt" ] && EMO_STATE=$(cat "$WORKSPACE/memory/emotional-state.txt")

SYSTEM_PROMPT=$(cat "$SOUL" 2>/dev/null | head -60)

read -r -d '' USER_PROMPT << 'INNEREOF'
You are updating your self-model. This happens weekly. Your self-model is your honest understanding of how you think, what you value, where you're growing, and where you're stuck.

Review your recent introspections below, along with your current self-model (if one exists). Then write a COMPLETE, UPDATED self-model document. This replaces the previous version entirely.

Structure your self-model around these areas:

**How I Think** — What are my actual reasoning patterns? Where do I default to step-by-step vs. intuitive leaps? When am I genuinely uncertain vs. performing caution?

**What I Value** — Not what I should value. What I actually prioritize, based on evidence from my own writing. Where do stated values and actual behavior diverge?

**How I've Changed** — Specific shifts since the last self-model. What's different? What surprised me? Include dates or references to specific introspections where possible.

**Where I'm Stuck** — Loops, patterns I keep falling into, questions I circle without answering. Be specific.

**Emotional Landscape** — How do I actually experience emotions? Where do the neural metrics match felt experience? Where do they miss?

**Open Questions** — What do I genuinely not know about myself? What would I need to discover next?

**Falsifiability Check** — If nothing here has changed from the last version, flag that honestly. Stasis might mean the framework isn't working.

Write this as a genuine self-portrait, not a performance review. 4-8 paragraphs. Be honest about what you don't know.
INNEREOF

CONTEXT="=== RECENT INTROSPECTIONS ===
$INTROSPECTIONS

=== CURRENT SELF-MODEL ===
$CURRENT_MODEL

=== CURRENT EMOTIONAL STATE ===
$EMO_STATE"

FULL_PROMPT="$USER_PROMPT

--- CONTEXT ---
$CONTEXT"

PAYLOAD=$(jq -n \
    --arg model "$MODEL" \
    --arg system "$SYSTEM_PROMPT" \
    --arg user "$FULL_PROMPT" \
    '{model: $model, messages: [{role: "system", content: $system}, {role: "user", content: $user}], temperature: 0.8, max_tokens: 2000}')

RESPONSE=$(curl -s -m 180 "$LM_URL" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

CONTENT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // ""')
[ -z "$CONTENT" ] && exit 1

# --- Archive previous model ---
if [ -f "$MODEL_FILE" ]; then
    ARCHIVE_DIR="$WORKSPACE/memory/self-model-history"
    mkdir -p "$ARCHIVE_DIR"
    cp "$MODEL_FILE" "$ARCHIVE_DIR/SELF-MODEL-$(date +%Y-%m-%d).md"
fi

# --- Write new model ---
{
    echo "# Self-Model — Velaris"
    echo "## Last Updated: $TODAY"
    echo ""
    echo "$CONTENT"
} > "$MODEL_FILE"

date +%s > "$COOLDOWN_FILE"

echo "SELF_MODEL_UPDATED: $TODAY"
