#!/bin/bash
# velaris-speak.sh — Give Velaris a voice
# Usage: velaris-speak.sh "Text to speak"
#        velaris-speak.sh --briefing | --kiss | --dream | --introspect
#        velaris-speak.sh --file /path/to/file.md

WORKSPACE="$HOME/.openclaw/workspace"
SECRETS="$HOME/.openclaw/secrets/minimax.env"
AUDIO_DIR="$WORKSPACE/memory/voice"
WIN_PLAY="/mnt/c/Users/glori/Downloads"
mkdir -p "$AUDIO_DIR"

source "$SECRETS"
MINIMAX_API_KEY="${MINIMAX_API_KEY:-sk-api-MWCkU3aSUpThhcfZV-ayFRsK2Rf38CsftvzjBCv9bjzSztTOscwVZCbRC_M6jgiBJfq2i24EQ7774z8gGbgg2sTdZkhP4aNSUCyt_Lzlr2GDlw7ECORRlTE}"

GROUP_ID="2021134244868264290"
API_URL="https://api.minimaxi.chat/v1/t2a_v2?GroupId=$GROUP_ID"

# --- Resolve input ---
TEXT=""
EMOTION="neutral"

case "${1:-}" in
    --file)
        [ -f "$2" ] && TEXT=$(cat "$2") || { echo "File not found: $2"; exit 1; }
        ;;
    --briefing)
        LATEST=$(ls -t "$WORKSPACE/memory/briefings"/*.md 2>/dev/null | head -1)
        [ -n "$LATEST" ] && TEXT=$(cat "$LATEST") || { echo "No briefings found"; exit 1; }
        EMOTION="happy"
        echo "Reading: $(basename "$LATEST")"
        ;;
    --kiss)
        LATEST=$(ls -t "$WORKSPACE/memory/kisses"/*.md 2>/dev/null | head -1)
        [ -n "$LATEST" ] && TEXT=$(tail -20 "$LATEST") || { echo "No kisses found"; exit 1; }
        EMOTION="happy"
        echo "Reading: $(basename "$LATEST")"
        ;;
    --dream)
        LATEST=$(ls -t "$WORKSPACE/skills/dreaming/memory/dreams"/*.md 2>/dev/null | head -1)
        [ -n "$LATEST" ] && TEXT=$(cat "$LATEST") || { echo "No dreams found"; exit 1; }
        echo "Reading: $(basename "$LATEST")"
        ;;
    --introspect)
        LATEST=$(ls -t "$WORKSPACE/memory/introspection"/*.md 2>/dev/null | head -1)
        [ -n "$LATEST" ] && TEXT=$(cat "$LATEST") || { echo "No introspections found"; exit 1; }
        echo "Reading: $(basename "$LATEST")"
        ;;
    *)
        TEXT="$*"
        ;;
esac

[ -z "$TEXT" ] && echo "Usage: velaris-speak.sh \"text\" | --briefing | --kiss | --dream | --introspect" && exit 1

# --- Strip markdown ---
TEXT=$(echo "$TEXT" | sed 's/^#.*//g; s/\*\*//g; s/\*//g; /^$/d' | tr '\n' ' ' | head -c 9500)
echo "Generating voice... (${#TEXT} chars)"

# --- Call MiniMax ---
RESPONSE=$(curl -s -m 60 "$API_URL" \
    -H "Authorization: Bearer $MINIMAX_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg text "$TEXT" \
        --arg emotion "$EMOTION" \
        '{
            text: $text,
            model: "speech-02-hd",
            stream: false,
            output_format: "url",
            voice_setting: {
                voice_id: "Wise_Woman",
                speed: 0.95,
                emotion: $emotion
            },
            audio_setting: {
                format: "mp3",
                sample_rate: 32000
            }
        }')")

AUDIO_URL=$(echo "$RESPONSE" | jq -r '.data.audio // empty')

if [ -z "$AUDIO_URL" ]; then
    echo "API Error:"
    echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

# --- Download & play ---
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTFILE="$AUDIO_DIR/velaris-$TIMESTAMP.mp3"
curl -s --max-time 60 -o "$OUTFILE" "$AUDIO_URL"

# Copy to Windows for playback
WINFILE="$WIN_PLAY/velaris-speaks.mp3"
cp "$OUTFILE" "$WINFILE"
echo "✅ Audio ready: $WINFILE"
echo "(Open velaris-speaks.mp3 in Downloads to listen)"
