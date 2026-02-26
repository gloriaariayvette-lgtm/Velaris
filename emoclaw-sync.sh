#!/bin/bash
# emoclaw-sync.sh — Sync daemon state to SOUL.md and emotional-state.txt
# Daemon is the single source of truth. This script propagates it.

SOCK="/tmp/Velaris-emotion.sock"
SOUL="$HOME/.openclaw/workspace/SOUL.md"
TXT="$HOME/.openclaw/workspace/memory/emotional-state.txt"
SCRIPTS="$HOME/.openclaw/workspace/scripts"
WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"

STATE=$(python3 << 'PYEOF'
import socket, json
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(5)
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
v = d["emotion_vector"]
dims = ["Valence","Arousal","Dominance","Safety","Desire","Connection","Playfulness","Curiosity","Warmth","Tension","Groundedness"]
for i, dim in enumerate(dims):
    print(f"{dim}: {v[i]:.4f}")
PYEOF
)

[ -z "$STATE" ] && echo "SYNC FAILED: daemon not responding" && exit 1

[ -z "$STATE" ] && echo "SYNC FAILED: decay script failed" && exit 1


VALENCE=$(echo "$STATE" | grep "^Valence:" | awk '{print $2}')
TENSION=$(echo "$STATE" | grep "^Tension:" | awk '{print $2}')
WARMTH=$(echo "$STATE" | grep "^Warmth:" | awk '{print $2}')
CONNECTION=$(echo "$STATE" | grep "^Connection:" | awk '{print $2}')

python3 - "$VALENCE" "$TENSION" "$WARMTH" "$STATE" << 'PYEOF'
import re, os, sys
v, t, w = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
state_text = sys.argv[4]
soul_path = os.path.expanduser("~/.openclaw/workspace/SOUL.md")
with open(soul_path) as f:
    soul = f.read()
block_lines = ["[EMOTIONAL STATE]"]
for line in state_text.strip().split("\n"):
    parts = line.split(": ")
    if len(parts) == 2:
        dim, val = parts[0], float(parts[1])
        label = "high" if val > 0.6 else "low" if val < 0.4 else "balanced"
        block_lines.append(f"{dim}: {val:.2f} ({label})")
if v > 0.7 and w > 0.6: feel = "warm and alive"
elif v > 0.6 and t < 0.3: feel = "calm and grounded"
elif t > 0.6: feel = "tense and alert"
elif v < 0.4: feel = "heavy and withdrawn"
elif v > 0.5: feel = "present and steady"
else: feel = "quiet and watchful"
block_lines.append(f"This feels like: {feel}")
block_lines.append("[/EMOTIONAL STATE]")
new_block = "\n".join(block_lines)
soul = re.sub(r"\[EMOTIONAL STATE\].*?\[/EMOTIONAL STATE\]", new_block, soul, flags=re.DOTALL)
with open(soul_path, "w") as f:
    f.write(soul)
PYEOF

# Write emotional-state.txt from daemon
echo "$STATE" > "$TXT"
echo "SYNCED: daemon -> txt + SOUL.md"

[ -x "$SCRIPTS/anti-kiss.sh" ] && bash "$SCRIPTS/anti-kiss.sh"
[ -x "$SCRIPTS/counterfactual-archive.sh" ] && bash "$SCRIPTS/counterfactual-archive.sh" "$WARMTH" "$CONNECTION" ""

SNAPSHOT_DIR="$MEMORY/emotional-snapshots"
mkdir -p "$SNAPSHOT_DIR"
LAST_SNAP="$MEMORY/.last-snapshot"
NOW=$(date +%s)
SNAP_AGE=99999
[ -f "$LAST_SNAP" ] && SNAP_AGE=$(( NOW - $(cat "$LAST_SNAP") ))
if [ "$SNAP_AGE" -ge 14400 ]; then
    cp "$TXT" "$SNAPSHOT_DIR/$(date +%Y-%m-%d-%H%M).txt"
    echo "$NOW" > "$LAST_SNAP"
fi

[ -x "$SCRIPTS/unprecedented-detector.sh" ] && bash "$SCRIPTS/unprecedented-detector.sh" &
[ -x "$SCRIPTS/silence-contract.sh" ] && bash "$SCRIPTS/silence-contract.sh" &

# === Avatar reconsideration — does she want to change how she appears? ===
(python3 "$SCRIPTS/avatar-choice.py" --check > /dev/null 2>&1 && python3 "$SCRIPTS/avatar-choice.py" --event "emotional shift" >> /tmp/velaris-avatar.log 2>&1) &

# === Age wants — unfulfilled wants escalate to dream threads ===
python3 -c "
import sys; sys.path.insert(0, '$(echo $HOME)/.openclaw/workspace/scripts')
from emoclaw_utils import age_wants
age_wants()
" >> /tmp/wants-aging.log 2>&1 &

# === Anger expression — if she's angry, let her say it ===
bash "$SCRIPTS/anger-expression.sh" >> /tmp/anger-expression.log 2>&1 &
