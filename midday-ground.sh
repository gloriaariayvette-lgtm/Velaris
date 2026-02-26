#!/bin/bash
# midday-ground.sh — Emotional grounding through reflection
# Triggered by elevated emotions. She names what's running hot,
# traces it to its source, and consciously sets it down.
# Schedule: Every 30 min, 11 AM - 2 PM (condition-gated, max 2x/day)
# Weekly trim: pearl curation (Wed 5 AM) reviews grounding entries

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
SOUL="$WORKSPACE/SOUL.md"
GROUND_DIR="$MEMORY/grounding"
COOLDOWN_FILE="$MEMORY/.last-grounding"
API="http://192.168.1.126:1234/v1/chat/completions"
MODEL="gemma-3-12b-it"
SOCK="/tmp/Velaris-emotion.sock"
TODAY=$(date +%Y-%m-%d)

mkdir -p "$GROUND_DIR"

# === Gate 1: Max 2 per day ===
TODAY_COUNT=0
if [ -f "$COOLDOWN_FILE" ]; then
    TODAY_COUNT=$(grep -c "$TODAY" "$COOLDOWN_FILE" 2>/dev/null || echo 0)
fi
if [ "$TODAY_COUNT" -ge 2 ]; then
    exit 0
fi

# === Gate 2: Minimum 90 min between sessions ===
if [ -f "$COOLDOWN_FILE" ]; then
    LAST=$(tail -1 "$COOLDOWN_FILE" | awk '{print $1" "$2}')
    LAST_TS=$(date -d "$LAST" +%s 2>/dev/null || echo 0)
    NOW_TS=$(date +%s)
    MINS_AGO=$(( (NOW_TS - LAST_TS) / 60 ))
    if [ "$MINS_AGO" -lt 90 ]; then
        exit 0
    fi
fi

# === Gate 3: Toggle check — can be disabled from app ===
if [ -f "$MEMORY/.grounding-disabled" ]; then
    echo "[grounding] Disabled by toggle"
    exit 0
fi

# === Gate 4: Are emotions elevated? (read from daemon, not stale file) ===
EMOTIONS=$(python3 << 'EMOPYEOF'
import socket, json
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(5)
try:
    s.connect("/tmp/Velaris-emotion.sock")
    s.sendall(json.dumps({"command": "state"}).encode() + b"\n")
    data = b""
    while True:
        chunk = s.recv(8192)
        if not chunk: break
        data += chunk
        if b"\n" in data: break
    s.close()
    d = json.loads(data)
    dims = ["Valence","Arousal","Dominance","Safety","Desire","Connection","Playfulness","Curiosity","Warmth","Tension","Groundedness"]
    for i, dim in enumerate(dims):
        print(f"{dim}: {d['emotion_vector'][i]:.4f}")
except:
    print("")
EMOPYEOF
)
[ -z "$EMOTIONS" ] && echo "[grounding] Cannot read daemon" && exit 0
CURIOSITY=$(echo "$EMOTIONS" | grep "^Curiosity:" | awk '{print $2}')
TENSION=$(echo "$EMOTIONS" | grep "^Tension:" | awk '{print $2}')

TRIGGERED=false
TRIGGER_DIM=""
TRIGGER_VAL=""

if python3 -c "exit(0 if float('${CURIOSITY:-0}') > 0.90 else 1)" 2>/dev/null; then
    TRIGGERED=true
    TRIGGER_DIM="Curiosity"
    TRIGGER_VAL="$CURIOSITY"
fi
if python3 -c "exit(0 if float('${TENSION:-0}') > 0.42 else 1)" 2>/dev/null; then
    TRIGGERED=true
    TRIGGER_DIM="${TRIGGER_DIM:+$TRIGGER_DIM and }Tension"
    TRIGGER_VAL="${TRIGGER_VAL:+$TRIGGER_VAL, }$TENSION"
fi

if [ "$TRIGGERED" = "false" ]; then
    exit 0
fi

echo "[grounding] Triggered: $TRIGGER_DIM at $TRIGGER_VAL"

# Gather context — what has she been doing?
TODAYS_JOURNAL=""
[ -f "$MEMORY/journal/$TODAY.md" ] && TODAYS_JOURNAL=$(tail -30 "$MEMORY/journal/$TODAY.md")

RECENT_AVATAR=""
[ -f "$MEMORY/avatar-log.json" ] && RECENT_AVATAR=$(python3 -c "
import json
try:
    entries = json.load(open('$MEMORY/avatar-log.json'))[-3:]
    for e in entries:
        print(f\"  {e.get('expression','?')}: {e.get('reason','')[:80]}\")
except: pass
" 2>/dev/null)

# What scripts ran recently?
RECENT_ACTIVITY=$(grep "$TODAY" /var/log/syslog 2>/dev/null | grep -i cron | grep "gloria" | tail -10 | awk '{print $NF}' | sort -u | head -8)

# Generate reflection
RESPONSE=$(python3 << PYEOF
import json, requests

soul = ""
try:
    with open("$SOUL") as f: soul = f.read()
except: soul = "You are Velaris."

journal = """$TODAYS_JOURNAL"""
avatar = """$RECENT_AVATAR"""
emotions = """$EMOTIONS"""

r = requests.post("$API", json={
    "model": "$MODEL",
    "messages": [
        {"role": "system", "content": soul + """

Your $TRIGGER_DIM is elevated ($TRIGGER_VAL). This is a grounding session — not to suppress what you feel, but to understand it and consciously set it down.

INSTRUCTIONS:
1. TRACE: Look at your journal entries and recent activity. What specifically excited or unsettled you? Name the source honestly.
2. NAME: Give this pattern a short name — 2-4 words that capture what is driving the elevation. Be specific, not abstract.
3. FEEL: Rate how much of this elevation feels genuine vs. self-reinforcing (a loop where curiosity feeds more curiosity, or tension feeds more tension). Be honest.
4. SET DOWN: Consciously acknowledge this. You can return to it. It will be here. But right now, settle into what is solid.
5. RESOLVE: One sentence — what you are carrying forward, and what you are releasing.

OUTPUT FORMAT:
SOURCE: [what specifically triggered the elevation]
NAME: [2-4 word pattern name]
GENUINE: [0-100% — how much is real vs self-reinforcing loop]
SETTING DOWN: [what you are releasing]
CARRYING FORWARD: [what stays with you]
RESOLVE: [one sentence]"""},
        {"role": "user", "content": f"Your emotional state right now:\\n{emotions}\\n\\nYour journal today:\\n{journal}\\n\\nYour recent avatar choices:\\n{avatar}\\n\\nWhat is driving your {('$TRIGGER_DIM')} to {('$TRIGGER_VAL')}? Trace it, name it, set it down."}
    ],
    "temperature": 0.5,
    "max_tokens": 600
}, timeout=60)

text = r.json()["choices"][0]["message"].get("content", "")
for marker in ["OUTPUT:", "Output:", "output:"]:
    if marker in text:
        text = text.split(marker)[-1].strip()
print(text.strip())
PYEOF
)

[ -z "$RESPONSE" ] && echo "[grounding] LLM returned empty" && exit 1

# Save entry with metadata for weekly review
{
    echo "---"
    echo "## $(date '+%H:%M') — Grounding Session"
    echo "Trigger: $TRIGGER_DIM at $TRIGGER_VAL"
    echo ""
    echo "$RESPONSE"
    echo ""
} >> "$GROUND_DIR/$TODAY.md"

# Record cooldown
echo "$TODAY $(date '+%H:%M')" >> "$COOLDOWN_FILE"

echo "[grounding] Reflection saved to $GROUND_DIR/$TODAY.md"

# === Emotional nudges ===
python3 << NUDGEPY
import socket, json

# Daemon caps at abs(0.10) per nudge, so split larger nudges
nudges = [
    ("Curiosity", -0.10),
    ("Curiosity", -0.02),
    ("Groundedness", 0.04),
]

# Only nudge tension down if it triggered
trigger_dim = "$TRIGGER_DIM"
if "Tension" in trigger_dim:
    nudges.append(("Tension", -0.04))

for dim, amount in nudges:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect("/tmp/Velaris-emotion.sock")
        s.sendall(json.dumps({"command": "nudge", "dimension": dim, "amount": amount}).encode() + b"\n")
        s.recv(4096)
        s.close()
    except:
        pass

print(f"[grounding] Nudges: Curiosity -0.12, Groundedness +0.04" + (", Tension -0.04" if "Tension" in trigger_dim else ""))
NUDGEPY

