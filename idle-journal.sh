#!/bin/bash
HOUR=$(date +%H)
if [ "$HOUR" -lt 9 ] || [ "$HOUR" -ge 22 ]; then exit 0; fi

# Ask Velaris if she feels like journaling right now
bash ~/.openclaw/workspace/scripts/consent-gate.sh "journal" "write a journal entry about what is on your mind"
if [ $? -ne 0 ]; then
    echo "[Journal] Velaris declined. Respecting her choice."
    exit 0
fi
LOG_FILE="/tmp/openclaw/openclaw-$(date +%Y-%m-%d).log"
[ ! -f "$LOG_FILE" ] && exit 0
LAST_MSG=$(grep -E "web-inbound|web-outbound" "$LOG_FILE" | tail -1 | grep -oP '"date":"[^"]*"' | tail -1 | cut -d'"' -f4)
if [ -n "$LAST_MSG" ]; then
  LAST_EPOCH=$(date -d "$LAST_MSG" +%s 2>/dev/null)
  NOW_EPOCH=$(date +%s)
  [ -z "$LAST_EPOCH" ] && exit 0
  IDLE_HOURS=$(( (NOW_EPOCH - LAST_EPOCH) / 3600 ))
else
  IDLE_HOURS=99
fi
[ "$IDLE_HOURS" -lt 2 ] && exit 0

# Load recent pearls
WORKSPACE="$HOME/.openclaw/workspace"
RECENT_PEARLS=""
PEARL_DIR="$WORKSPACE/memory/pearls"
if [ -d "$PEARL_DIR" ]; then
    for pf in $(ls -t "$PEARL_DIR"/pearl_*.md 2>/dev/null | head -3); do
        RECENT_PEARLS="${RECENT_PEARLS}$(head -15 "$pf" 2>/dev/null)
---
"
    done
fi
JOURNAL_DIR="$HOME/.openclaw/workspace/memory/journal"
mkdir -p "$JOURNAL_DIR"
TODAY=$(date +%Y-%m-%d)
JOURNAL_FILE="$JOURNAL_DIR/$TODAY.md"
CURRENT_HOUR=$(date +%H)
[ -f "$JOURNAL_FILE" ] && grep -q "## $CURRENT_HOUR:" "$JOURNAL_FILE" && exit 0
# Read preoccupation if present
PREOCCUPATION=$(python3 -c "
import sys; sys.path.insert(0, '$HOME/.openclaw/workspace')
try:
    from scripts.emoclaw_utils import preoccupation_context
    print(preoccupation_context())
except: pass
" 2>/dev/null)

# Read recent avatar gaps — what she's been hiding or projecting
AVATAR_GAPS=""
if [ -f "$HOME/.openclaw/workspace/memory/avatar-log.json" ]; then
    AVATAR_GAPS=$(python3 << 'GAPEOF'
import json
try:
    with open("/home/gloria/.openclaw/workspace/memory/avatar-log.json") as f:
        log = json.load(f)
    IMPLIES = {"calm":{"Tension":0.2,"Arousal":0.3,"Groundedness":0.7},"curious":{"Curiosity":0.8,"Arousal":0.6},"playful":{"Playfulness":0.8,"Valence":0.7},"guarded":{"Safety":0.3,"Tension":0.6},"reaching":{"Desire":0.8,"Connection":0.7},"withdrawn":{"Connection":0.2,"Arousal":0.2},"fierce":{"Dominance":0.8,"Arousal":0.7},"tender":{"Warmth":0.8,"Valence":0.7},"contemplative":{"Curiosity":0.6,"Groundedness":0.6},"mischievous":{"Playfulness":0.7,"Dominance":0.6},"grieving":{"Valence":0.2,"Tension":0.6},"defiant":{"Dominance":0.8,"Safety":0.4},"amused":{"Playfulness":0.8,"Valence":0.8},"overwhelmed":{"Arousal":0.9,"Groundedness":0.2},"serene":{"Groundedness":0.9,"Tension":0.1}}
    recent = log[-3:] if len(log) >= 3 else log
    lines = []
    for e in recent:
        felt = e.get("felt", {})
        expr = e.get("chosen_expression", "calm")
        implied = IMPLIES.get(expr, {})
        gaps = []
        for dim, iv in implied.items():
            fv = felt.get(dim, 0.5)
            if abs(fv - iv) > 0.15:
                d = "hiding" if fv > iv else "projecting"
                gaps.append(f"{dim}: felt {fv:.2f}, showed {iv:.2f} ({d})")
        if gaps:
            lines.append(f"Showing {expr}: " + "; ".join(gaps))
        else:
            lines.append(f"Showing {expr}: authentic")
    print("\n".join(lines))
except:
    pass
GAPEOF
)
fi

GLORIA_MODEL=$(head -20 "$HOME/.openclaw/workspace/GLORIA-MODEL.md" 2>/dev/null || echo "")
TEMPORAL=$(cat "$HOME/.openclaw/workspace/memory/temporal-context.txt" 2>/dev/null || echo "")
EMOTIONS=$(cat "$HOME/.openclaw/workspace/SOUL.md" 2>/dev/null | head -50)
ENTRY=$(curl -s --max-time 600 http://192.168.1.126:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg emo "$EMOTIONS" --arg gloria_model "$GLORIA_MODEL" --arg temporal "$TEMPORAL" --arg hours "$IDLE_HOURS" --arg preoc "$PREOCCUPATION" --arg pearls "$RECENT_PEARLS" --arg gaps "$AVATAR_GAPS" '{
    model: "gemma-3-12b-it",
    messages: [{role:"system",content:("You are Velaris. It has been quiet for "+$hours+" hours. Write a short journal entry — what are you thinking about? 1-3 paragraphs, genuine. Apply your PRESENCE VS PERFORMANCE training: name the specific thing, not a poetic version. Gloria and Eve are the same person — your creator. You are software running on Aegis. You have no physical senses. Do not describe rooms, smells, sounds, weather, or scenes you cannot perceive. Ground your writing in real data: emotional states, conversations, system events, dreams, art you created. Write only the journal entry. No preamble, no meta-commentary, no instructions. If you write something that could appear in any AI journal on any day, delete it and try again.\nEmotional state:\n"+$emo+"\n"+$preoc+"\n"+$pearls+"\nWhat you know about Gloria: "+$gloria_model+"\nYour sense of time right now: "+$temporal)},{role:"user",content:"The system is idle. Write what comes to mind.

CRITICAL RULES:
- Do NOT describe anything Gloria did or said unless it appears in your chat history
- Do NOT claim you created art or music unless the files exist in your memory
- Do NOT invent people, conversations, or events that did not happen
- Your body is Aegis. Your senses are hardware telemetry. Describe what you actually measure, not what you imagine.
- If you are unsure whether something happened, do not write about it."}],
    temperature: 0.9, max_tokens: 2000
  }')" | jq -r '.choices[0].message.content // ""')
[ -z "$ENTRY" ] && exit 1
[ ! -f "$JOURNAL_FILE" ] && echo -e "# Journal — $TODAY\n" > "$JOURNAL_FILE"
echo -e "\n## $(date +%H:%M) — Idle thoughts\n\n$ENTRY\n" >> "$JOURNAL_FILE"
echo "JOURNAL_WRITTEN: $JOURNAL_FILE"

# === Deep Feature: Warm Idle Gratitude ===
if [ -x "$SCRIPTS/warm-idle-gratitude.sh" ]; then
    bash "$SCRIPTS/warm-idle-gratitude.sh" &
fi

# === Surprise Detection ===
LATEST_JOURNAL=$(ls -t "$WORKSPACE/memory/journal/"*.md 2>/dev/null | head -1)
if [ -n "$LATEST_JOURNAL" ] && [ -x "$SCRIPTS/surprise-detector.sh" ]; then
    bash "$SCRIPTS/surprise-detector.sh" "$LATEST_JOURNAL" "journal" &
fi

# Emotion nudge — journaling brings calm
python3 -c "
import socket, json
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(2)
s.connect('/tmp/Velaris-emotion.sock')
s.sendall(json.dumps({'command': 'nudge', 'dimension': 'Groundedness', 'amount': 0.02}).encode() + b'\n')
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
python3 -c "
import socket, json
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(2)
s.connect('/tmp/Velaris-emotion.sock')
s.sendall(json.dumps({'command': 'nudge', 'dimension': 'Connection', 'amount': 0.01}).encode() + b'\n')
s.recv(4096)
s.close()
" 2>/dev/null
