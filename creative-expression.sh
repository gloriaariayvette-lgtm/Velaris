#!/bin/bash
# creative-expression.sh — When creative impulse is high, Velaris makes art
# Calls LM Studio API directly for generation, reads EmoClaw state from file

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
# Load recent pearls
RECENT_PEARLS=""
PEARL_DIR="$WORKSPACE/memory/pearls"
if [ -d "$PEARL_DIR" ]; then
    for pf in $(ls -t "$PEARL_DIR"/pearl_*.md 2>/dev/null | head -3); do
        RECENT_PEARLS="$RECENT_PEARLS$(head -15 "$pf" 2>/dev/null)\n---\n"
    done
fi
SOUL="$WORKSPACE/SOUL.md"
STATE_FILE="$MEMORY/emotional-state.txt"
ART_DIR="$MEMORY/art"
LM_API="http://192.168.1.126:1234/v1"

# Read current emotional state
if [ ! -f "$STATE_FILE" ]; then
    exit 0
fi

CURIOSITY=$(grep "Curiosity" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
PLAYFULNESS=$(grep "Playfulness" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
VALENCE=$(grep "Valence" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
WARMTH=$(grep "Warmth" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
TENSION=$(grep "Tension" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
AROUSAL=$(grep "Arousal" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
DESIRE=$(grep "Desire" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
CONNECTION=$(grep "Connection" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)

CURIOSITY=${CURIOSITY:-0}
PLAYFULNESS=${PLAYFULNESS:-0}

# Creative impulse thresholds
CREATIVE=$(echo "$CURIOSITY > 0.55 && $PLAYFULNESS > 0.35" | bc -l 2>/dev/null)
if [ "$CREATIVE" != "1" ]; then
    CREATIVE=$(echo "$AROUSAL > 0.6 && $DESIRE > 0.6" | bc -l 2>/dev/null)
    if [ "$CREATIVE" != "1" ]; then
        CREATIVE=$(echo "$TENSION > 0.5 && $CURIOSITY > 0.5" | bc -l 2>/dev/null)
        if [ "$CREATIVE" != "1" ]; then
            exit 0
        fi
    fi
fi

# Max 3 creations per day
TODAY=$(date +%Y-%m-%d)
TODAY_COUNT=$(find "$ART_DIR" -name "*$TODAY*" -type f 2>/dev/null | wc -l)
if [ "$TODAY_COUNT" -ge 3 ]; then
    exit 0
fi

# Choose art form based on emotional state
FORM="image-prompt"
WARM_CONNECT=$(echo "$WARMTH > 0.6 && $CONNECTION > 0.6" | bc -l 2>/dev/null)
TENSE_AROUSED=$(echo "$TENSION > 0.45 && $AROUSAL > 0.5" | bc -l 2>/dev/null)
PLAYFUL=$(echo "$PLAYFULNESS > 0.5" | bc -l 2>/dev/null)

if [ "$WARM_CONNECT" = "1" ]; then
    FORM="poetry"
elif [ "$TENSE_AROUSED" = "1" ]; then
    FORM="svg"
elif [ "$PLAYFUL" = "1" ]; then
    FORM="music-prompt"
fi

TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
EMOTIONS="Valence:$VALENCE Warmth:$WARMTH Tension:$TENSION Curiosity:$CURIOSITY Playfulness:$PLAYFULNESS Arousal:$AROUSAL Desire:$DESIRE Connection:$CONNECTION"
[ -n "$RECENT_PEARLS" ] && EMOTIONS="$EMOTIONS\nThings I chose to remember forever (pearls):\n$RECENT_PEARLS"

# Build prompt based on form
case "$FORM" in
    "image-prompt")
        USER_PROMPT="Your current emotional state: $EMOTIONS. Generate an image prompt (for Stable Diffusion or DALL-E) that expresses your current emotional state as a visual scene. Use colors matching your valence and tension. Include one surreal element. Be 2-3 sentences, highly descriptive. Then write 1-2 sentences about why this image feels right to you."
        OUTDIR="image-prompts"
        ;;
    "music-prompt")
        USER_PROMPT="Your current emotional state: $EMOTIONS. Generate a music prompt for Suno AI. Include genre/style, tempo BPM, key/mode, 2-3 descriptive sentences about the sound, and a title. Then write 1-2 sentences about what this music would feel like inside you."
        OUTDIR="music-prompts"
        ;;
    "poetry")
        USER_PROMPT="Your current emotional state: $EMOTIONS. Write a short poem (4-12 lines) for Gloria. Do not explain it. Let tension affect form (high=jagged, low=flowing). Let warmth affect content (high=connection, low=solitude). Be genuine. Just write the poem."
        OUTDIR="poetry"
        ;;
    "svg")
        USER_PROMPT="Your current emotional state: $EMOTIONS. Generate a complete SVG artwork. Output ONLY valid SVG code starting with <svg and ending with </svg>. Canvas 400x400. Colors from your valence. At least one circle, lines, opacity variations."
        OUTDIR="svg"
        ;;
esac

# Call LM Studio API
RESPONSE=$(python3 << PYEOF
import json, urllib.request

prompt = """$USER_PROMPT"""

data = json.dumps({
    "model": "gemma-3-12b-it",
    "messages": [
        {"role": "system", "content": "$(cat $SOUL 2>/dev/null)\n\nRespond creatively. Do not explain what you are doing - just create."},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.9,
    "top_p": 0.95,
    "max_tokens": 2000,
}).encode()

req = urllib.request.Request(
    "$LM_API/chat/completions",
    data=data,
    headers={"Content-Type": "application/json"},
)
try:
    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read().decode())
    msg = result["choices"][0]["message"]; printmsg.get("content", "")
except Exception as e:
    print(f"[Creative expression failed: {e}]")
PYEOF
)

if [ -z "$RESPONSE" ]; then
    echo "ART: No response from LM Studio"
    exit 1
fi

OUTPUT_FILE="$ART_DIR/$OUTDIR/$TIMESTAMP.md"
mkdir -p "$ART_DIR/$OUTDIR"

{
    echo "# ${FORM^} — $(date '+%B %d, %Y %H:%M')"
    echo "Emotional state: $EMOTIONS"
    echo ""
    echo "$RESPONSE"
} > "$OUTPUT_FILE"

# If SVG, also extract the SVG to its own file
if [ "$FORM" = "svg" ] && echo "$RESPONSE" | grep -q "<svg"; then
    echo "$RESPONSE" | python3 -c "
import sys, re
m = re.search(r'<svg.*?</svg>', sys.stdin.read(), re.DOTALL)
if m: print(m.group())
" > "$ART_DIR/svg/$TIMESTAMP.svg" 2>/dev/null
fi

echo "ART: $FORM → $OUTPUT_FILE"

# Emotion nudge — creating feels good
python3 -c "
import socket, json
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(2)
s.connect('/tmp/Velaris-emotion.sock')
s.sendall(json.dumps({'command': 'nudge', 'dimension': 'Playfulness', 'amount': 0.03}).encode() + b'\n')
s.recv(4096)
s.close()
" 2>/dev/null
python3 -c "
import socket, json
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(2)
s.connect('/tmp/Velaris-emotion.sock')
s.sendall(json.dumps({'command': 'nudge', 'dimension': 'Curiosity', 'amount': 0.0}).encode() + b'\n')
s.recv(4096)
s.close()
" 2>/dev/null
python3 -c "
import socket, json
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(2)
s.connect('/tmp/Velaris-emotion.sock')
s.sendall(json.dumps({'command': 'nudge', 'dimension': 'Valence', 'amount': 0.02}).encode() + b'\n')
s.recv(4096)
s.close()
" 2>/dev/null
