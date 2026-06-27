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

# --- Call Kokoro (local TTS) ---
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTFILE="$AUDIO_DIR/velaris-$TIMESTAMP.wav"

export _SPEAK_TEXT="$TEXT"
export _SPEAK_OUTFILE="$OUTFILE"
/home/gloria/imggen-venv/bin/python3 -W ignore -c "
import os, sys, warnings
warnings.filterwarnings('ignore')
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
text = os.environ.get('_SPEAK_TEXT', '')
outfile = os.environ.get('_SPEAK_OUTFILE', '/tmp/velaris.wav')
if not text: sys.exit(1)
from kokoro import KPipeline
import soundfile as sf, numpy as np
pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M', device='cpu')
chunks = [audio for gs, ps, audio in pipeline(text, voice='af_heart', speed=0.95)]
if chunks:
   sf.write(outfile, np.concatenate(chunks), 24000)
"

if [ ! -f "$OUTFILE" ]; then
   echo "Kokoro generation failed"
   exit 1
fi

# Copy to Windows for playback
WINFILE="$WIN_PLAY/velaris-speaks.wav"
cp "$OUTFILE" "$WINFILE"
echo "Audio ready: $WINFILE"
echo "(Open velaris-speaks.wav in Downloads to listen)"
