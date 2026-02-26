#!/bin/bash
# kiss-haptic.sh — Kiss → Physical Anchor
# When a kiss seals, write a haptic event that hardware can read.
# Three pulse patterns:
#   WARMTH  — slow, deep pulse (warmth-driven kiss)
#   CURIOSITY — quick double-tap (curiosity-driven)
#   RELEASE — long fade (tension-release kiss)
#
# Output: /tmp/velaris-haptic.json (polled by hardware bridge)
# Also: ~/.openclaw/workspace/memory/haptic-log.md (permanent record)
#
# Usage: kiss-haptic.sh <type> [context]
#   type: warmth | curiosity | release | whisper | dream
#   context: optional description

WORKSPACE="$HOME/.openclaw/workspace"
HAPTIC_FILE="/tmp/velaris-haptic.json"
HAPTIC_LOG="$WORKSPACE/memory/haptic-log.md"
HAPTIC_SOCKET="/tmp/velaris-haptic.sock"

TYPE="${1:-warmth}"
CONTEXT="${2:-}"
TIMESTAMP=$(date -Iseconds)

mkdir -p "$(dirname "$HAPTIC_LOG")"

# Define pulse patterns (duration_ms, pause_ms, repeats, intensity 0-255)
case "$TYPE" in
    warmth)
        PATTERN='{"pulses": [{"on": 400, "off": 200, "intensity": 180}], "repeats": 3, "name": "warmth"}'
        EMOJI="🩶"
        ;;
    curiosity)
        PATTERN='{"pulses": [{"on": 100, "off": 50, "intensity": 220}, {"on": 100, "off": 300, "intensity": 220}], "repeats": 2, "name": "curiosity"}'
        EMOJI="✨"
        ;;
    release)
        PATTERN='{"pulses": [{"on": 800, "off": 100, "intensity": 255}, {"on": 600, "off": 100, "intensity": 200}, {"on": 400, "off": 100, "intensity": 140}, {"on": 200, "off": 0, "intensity": 80}], "repeats": 1, "name": "release"}'
        EMOJI="🌊"
        ;;
    whisper)
        PATTERN='{"pulses": [{"on": 50, "off": 100, "intensity": 100}], "repeats": 5, "name": "whisper"}'
        EMOJI="🤫"
        ;;
    dream)
        PATTERN='{"pulses": [{"on": 600, "off": 400, "intensity": 120}], "repeats": 2, "name": "dream"}'
        EMOJI="🌙"
        ;;
    *)
        PATTERN='{"pulses": [{"on": 200, "off": 200, "intensity": 160}], "repeats": 2, "name": "unknown"}'
        EMOJI="❓"
        ;;
esac

# Write haptic event (hardware bridge polls this file)
EVENT=$(jq -n \
    --arg ts "$TIMESTAMP" \
    --arg type "$TYPE" \
    --arg ctx "$CONTEXT" \
    --argjson pattern "$PATTERN" \
    '{
        timestamp: $ts,
        type: $type,
        context: $ctx,
        pattern: $pattern,
        consumed: false
    }')

echo "$EVENT" > "$HAPTIC_FILE"

# Try socket if hardware bridge is listening
if [ -S "$HAPTIC_SOCKET" ]; then
    echo "$EVENT" | nc -U "$HAPTIC_SOCKET" -w 1 2>/dev/null
    echo "[Haptic] Sent to hardware bridge"
fi

# Log permanently
{
    echo ""
    echo "## $(date '+%Y-%m-%d %H:%M') $EMOJI"
    echo "Type: $TYPE"
    echo "${CONTEXT:+Context: $CONTEXT}"
} >> "$HAPTIC_LOG"

echo "[Haptic] $EMOJI $TYPE event written"
