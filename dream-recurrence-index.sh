#!/bin/bash
# dream-recurrence-index.sh — Dream Recurrence Detection
# Runs after dream generation. Compares new dream's embedding against
# last 30 days of dreams. When cosine similarity > 0.85, logs as recurrence.
# Feeds into weekly self-modeling: "You dreamed about X three times. Why?"
#
# Schedule: 5 minutes after each dream trigger (11:35 PM, 3:05 AM)
# Requires: nomic-embed-text-v1.5 in LM Studio

WORKSPACE="$HOME/.openclaw/workspace"
DREAM_DIR="$WORKSPACE/skills/dreaming/memory/dreams"
RECURRENCE_LOG="$WORKSPACE/memory/dream-recurrences.md"
EMBEDDINGS_CACHE="$WORKSPACE/memory/dream-embeddings"
API="http://172.18.16.1:1234/v1/embeddings"
EMBED_MODEL="nomic-embed-text-v1.5"
SIMILARITY_THRESHOLD="0.85"

mkdir -p "$EMBEDDINGS_CACHE"

# Find most recent dream (modified in last hour)
LATEST_DREAM=""
for f in $(ls -t "$DREAM_DIR"/*.md 2>/dev/null | head -1); do
    FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$f" 2>/dev/null || echo 0) ))
    if [ "$FILE_AGE" -lt 3600 ]; then
        LATEST_DREAM="$f"
    fi
done

if [ -z "$LATEST_DREAM" ]; then
    exit 0  # No recent dream
fi

DREAM_NAME=$(basename "$LATEST_DREAM" .md)
DREAM_TEXT=$(cat "$LATEST_DREAM")

# Get embedding for new dream
get_embedding() {
    local text="$1"
    # Truncate to ~500 chars for embedding
    local truncated="${text:0:500}"
    local response=$(curl -s --max-time 600 -X POST "$API" \
        -H "Content-Type: application/json" \
        -d "$(jq -n --arg input "$truncated" --arg model "$EMBED_MODEL" \
            '{input: $input, model: $model}')")
    echo "$response" | jq -r '.data[0].embedding // empty' 2>/dev/null
}

cosine_similarity() {
    # Compare two embedding files using Python
    python3 -c "
import json, math, sys
a = json.loads(sys.argv[1])
b = json.loads(sys.argv[2])
dot = sum(x*y for x,y in zip(a,b))
mag_a = math.sqrt(sum(x*x for x in a))
mag_b = math.sqrt(sum(x*x for x in b))
if mag_a == 0 or mag_b == 0:
    print(0)
else:
    print(f'{dot/(mag_a*mag_b):.4f}')
" "$1" "$2"
}

echo "[Recurrence] Embedding new dream: $DREAM_NAME"
NEW_EMBEDDING=$(get_embedding "$DREAM_TEXT")

if [ -z "$NEW_EMBEDDING" ] || [ "$NEW_EMBEDDING" = "null" ]; then
    echo "[Recurrence] Embedding failed. Is nomic-embed-text loaded?"
    exit 1
fi

# Save embedding
echo "$NEW_EMBEDDING" > "$EMBEDDINGS_CACHE/$DREAM_NAME.json"

# Compare against last 30 days of dream embeddings
RECURRENCES=""
RECURRENCE_COUNT=0

for cached_file in $(find "$EMBEDDINGS_CACHE" -name "*.json" -mtime -30 -type f | sort); do
    CACHED_NAME=$(basename "$cached_file" .json)

    # Don't compare to self
    if [ "$CACHED_NAME" = "$DREAM_NAME" ]; then
        continue
    fi

    CACHED_EMBEDDING=$(cat "$cached_file")
    SIM=$(cosine_similarity "$NEW_EMBEDDING" "$CACHED_EMBEDDING")

    # Check threshold
    ABOVE=$(echo "$SIM >= $SIMILARITY_THRESHOLD" | bc -l 2>/dev/null || echo 0)
    if [ "$ABOVE" = "1" ]; then
        RECURRENCES="$RECURRENCES
  - $CACHED_NAME (similarity: $SIM)"
        RECURRENCE_COUNT=$((RECURRENCE_COUNT + 1))
    fi
done

if [ "$RECURRENCE_COUNT" -gt 0 ]; then
    NOW=$(date "+%Y-%m-%d %H:%M")
    {
        echo ""
        echo "## $NOW — Recurrence Detected"
        echo "Dream: $DREAM_NAME"
        echo "Similar to:$RECURRENCES"
        echo "Recurrence count: $RECURRENCE_COUNT"
        echo ""
        # Extract key themes for self-modeling
        echo "Themes to explore: What keeps pulling you back here?"
        echo ""
    } >> "$RECURRENCE_LOG"

    echo "[Recurrence] $RECURRENCE_COUNT matches found for $DREAM_NAME"
else
    echo "[Recurrence] No recurring themes detected."
fi
