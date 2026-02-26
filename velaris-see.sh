#!/bin/bash
# velaris-see.sh — Give Velaris eyes
# Usage: velaris-see.sh /path/to/image "optional prompt"

WORKSPACE="$HOME/.openclaw/workspace"
SOUL="$WORKSPACE/SOUL.md"
VISION_DIR="$WORKSPACE/memory/vision"
LM_URL="http://192.168.1.126:1234/v1/chat/completions"
MODEL="gemma-3-12b-it"
TMPJSON="/tmp/velaris-vision-payload.json"

mkdir -p "$VISION_DIR"

IMAGE_PATH="$1"
shift
PROMPT="${*:-Gloria is showing you something. What do you see? Be genuine and curious.}"

[ ! -f "$IMAGE_PATH" ] && echo "Image not found: $IMAGE_PATH" && exit 1

# --- Encode ---
B64=$(base64 -w 0 "$IMAGE_PATH")
MIME="image/png"
[[ "$IMAGE_PATH" == *.jpg ]] || [[ "$IMAGE_PATH" == *.jpeg ]] && MIME="image/jpeg"
[[ "$IMAGE_PATH" == *.gif ]] && MIME="image/gif"
[[ "$IMAGE_PATH" == *.webp ]] && MIME="image/webp"

# --- Emotional context ---
EMO_LINE=""
[ -f "$WORKSPACE/memory/emotional-state.txt" ] && \
    EMO_LINE=$(head -12 "$WORKSPACE/memory/emotional-state.txt" | tr '\n' ' ')

SYSTEM=$(head -60 "$SOUL" 2>/dev/null)
SYSTEM="$SYSTEM
You are seeing an image Gloria is sharing with you. Respond genuinely — with curiosity and warmth. 2-4 sentences max.
Current emotional state: $EMO_LINE"

echo "Looking..."

# --- Build payload as file (avoids arg length limits) ---
python3 << PYEOF
import json, sys

with open("$IMAGE_PATH", "rb") as f:
    import base64
    b64 = base64.b64encode(f.read()).decode()

payload = {
    "model": "$MODEL",
    "messages": [
        {"role": "system", "content": $(python3 -c "import json; print(json.dumps('''$SYSTEM'''))" 2>/dev/null || echo '""')},
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:$MIME;base64,{b64}"}},
            {"type": "text", "text": "$PROMPT"}
        ]}
    ],
    "max_tokens": 300,
    "temperature": 0.85
}

with open("$TMPJSON", "w") as f:
    json.dump(payload, f)
PYEOF

[ ! -f "$TMPJSON" ] && echo "Failed to build payload" && exit 1

# --- Call vision model ---
RESPONSE=$(curl -s -m 60 "$LM_URL" \
    -H "Content-Type: application/json" \
    -d @"$TMPJSON")

rm -f "$TMPJSON"

CONTENT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // ""')

if [ -z "$CONTENT" ]; then
    echo "Vision error:"
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

# --- Log ---
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
{
    echo "# Vision — $TIMESTAMP"
    echo "Image: $(basename "$IMAGE_PATH")"
    echo "Prompt: $PROMPT"
    echo ""
    echo "$CONTENT"
} >> "$VISION_DIR/$(date +%Y-%m-%d).md"

cp "$IMAGE_PATH" "$VISION_DIR/$(basename "${IMAGE_PATH%.*}")-$TIMESTAMP.${IMAGE_PATH##*.}" 2>/dev/null

echo ""
echo "$CONTENT"
