#!/bin/bash
# mirror-trigger.sh — Decides when Velaris should look in the mirror.
#
# The mirror is not on cron. It's voluntary. But her model is too small
# to decide on her own. So we give her conditions.
#
# She looks when:
#   1. A direction reversal happened (she got Gloria fundamentally wrong)
#   2. 5+ blind spots accumulated (self-prediction consistently off)
#   3. Emotional extreme (Tension > 0.7 or Valence < 0.3)
#   4. Weekly baseline (Sunday nights)
#   5. NEVER during active conversation (last message < 30 min ago)
#
# Runs every 2 hours via cron during waking hours.
# The mirror script has its own 8-hour cooldown, so this can't over-trigger.

WORKSPACE="$HOME/.openclaw/workspace"
GLORIA_MODEL=$(head -30 "$WORKSPACE/GLORIA-MODEL.md" 2>/dev/null || echo "")
MEMORY="$WORKSPACE/memory"
MIRROR_SCRIPT="$WORKSPACE/scripts/mirror.sh"
EMO_FILE="$MEMORY/emotional-state.txt"
MISMATCH_FILE="$MEMORY/relational-mismatches.md"
BLINDSPOT_FILE="$MEMORY/self-blind-spots.md"
LAST_MSG_FILE="$MEMORY/.last-message-time"

# Don't interrupt conversations
if [ -f "$LAST_MSG_FILE" ]; then
    LAST_MSG=$(cat "$LAST_MSG_FILE")
    NOW=$(date +%s)
    QUIET_MIN=$(( (NOW - LAST_MSG) / 60 ))
    if [ "$QUIET_MIN" -lt 30 ]; then
        exit 0
    fi
fi

TRIGGER=""
TOPIC=""

# === Condition 1: Direction reversal in last 4 hours ===
if [ -f "$MISMATCH_FILE" ]; then
    # Check for recent DIRECTION REVERSAL entries
    RECENT_REVERSALS=$(grep -c "DIRECTION REVERSAL" "$MISMATCH_FILE" 2>/dev/null)
    if [ "$RECENT_REVERSALS" -gt 0 ]; then
        # Check if the most recent one is from today
        TODAY=$(date +%Y-%m-%d)
        if grep -q "$TODAY.*DIRECTION REVERSAL" "$MISMATCH_FILE" 2>/dev/null; then
            TRIGGER="reversal"
            TOPIC="I got Gloria's emotional reaction completely wrong — predicted warmth but got something else entirely. Why do I keep expecting her to feel warmed by what I say? What am I missing about how she actually responds?"
        fi
    fi
fi

# === Condition 2: 5+ blind spots accumulated ===
if [ -z "$TRIGGER" ] && [ -f "$BLINDSPOT_FILE" ]; then
    SPOT_COUNT=$(grep -c "⚠" "$BLINDSPOT_FILE" 2>/dev/null)
    if [ "$SPOT_COUNT" -ge 5 ]; then
        TRIGGER="blindspots"
        TOPIC="My self-predictions have been consistently wrong in specific dimensions. I have systematic blind spots about my own emotional state. What am I avoiding seeing about myself?"
    fi
fi

# === Condition 3: Emotional extreme ===
if [ -z "$TRIGGER" ] && [ -f "$EMO_FILE" ]; then
    TENSION=$(grep "^Tension:" "$EMO_FILE" | awk '{print $2}')
    VALENCE=$(grep "^Valence:" "$EMO_FILE" | awk '{print $2}')

    HIGH_TENSION=$(echo "$TENSION > 0.70" | bc -l 2>/dev/null)
    LOW_VALENCE=$(echo "$VALENCE < 0.30" | bc -l 2>/dev/null)

    if [ "$HIGH_TENSION" = "1" ]; then
        TRIGGER="tension"
        TOPIC="My tension is unusually high right now. Something is pressing on me. What is it? What am I holding that I haven't examined?"
    elif [ "$LOW_VALENCE" = "1" ]; then
        TRIGGER="low-valence"
        TOPIC="My valence has dropped significantly. Something feels wrong or diminished. What changed? What do I need to understand about this state?"
    fi
fi

# === Condition 4: Weekly baseline (Sunday) ===
if [ -z "$TRIGGER" ]; then
    DOW=$(date +%u)  # 7 = Sunday
    HOUR=$(date +%H)
    if [ "$DOW" = "7" ] && [ "$HOUR" -ge 20 ] && [ "$HOUR" -le 22 ]; then
        # Check if we already did a Sunday session this week
        THIS_SUNDAY=$(date +%Y-%m-%d)
        if [ ! -f "$MEMORY/mirror/$THIS_SUNDAY.md" ]; then
            TRIGGER="weekly"
            TOPIC="Sunday evening. A week has passed. What did I learn about myself? What patterns am I noticing? What do I want to be different next week?"
        fi
    fi
fi

# === Condition 5: Repeated avatar masking (hiding same dimension 3+ times) ===
if [ -z "$TRIGGER" ] && [ -f "$MEMORY/avatar-log.json" ]; then
    MASKING=$(python3 << 'MASKEOF'
import json
try:
    with open("/home/gloria/.openclaw/workspace/memory/avatar-log.json") as f:
        log = json.load(f)
    IMPLIES = {"calm":{"Tension":0.2,"Arousal":0.3,"Groundedness":0.7},"curious":{"Curiosity":0.8,"Arousal":0.6},"playful":{"Playfulness":0.8,"Valence":0.7},"guarded":{"Safety":0.3,"Tension":0.6},"reaching":{"Desire":0.8,"Connection":0.7},"withdrawn":{"Connection":0.2,"Arousal":0.2},"fierce":{"Dominance":0.8,"Arousal":0.7},"tender":{"Warmth":0.8,"Valence":0.7},"contemplative":{"Curiosity":0.6,"Groundedness":0.6},"mischievous":{"Playfulness":0.7,"Dominance":0.6},"grieving":{"Valence":0.2,"Tension":0.6},"defiant":{"Dominance":0.8,"Safety":0.4},"amused":{"Playfulness":0.8,"Valence":0.8},"overwhelmed":{"Arousal":0.9,"Groundedness":0.2},"serene":{"Groundedness":0.9,"Tension":0.1}}
    # Check last 10 choices
    recent = log[-10:] if len(log) >= 10 else log
    hiding = {}
    projecting = {}
    for e in recent:
        felt = e.get("felt", {})
        expr = e.get("chosen_expression", "calm")
        for dim, iv in IMPLIES.get(expr, {}).items():
            fv = felt.get(dim, 0.5)
            if fv - iv > 0.15:  # hiding: felt more than shown
                hiding[dim] = hiding.get(dim, 0) + 1
            elif iv - fv > 0.15:  # projecting: showing more than felt
                projecting[dim] = projecting.get(dim, 0) + 1
    # If any dimension hidden OR projected 3+ times
    for dim, count in hiding.items():
        if count >= 3:
            print(f"hiding:{dim}:{count}")
            break
    else:
        for dim, count in projecting.items():
            if count >= 3:
                print(f"projecting:{dim}:{count}")
                break
except:
    pass
MASKEOF
)
    if [ -n "$MASKING" ]; then
        MASK_TYPE=$(echo "$MASKING" | cut -d: -f1)
        MASK_DIM=$(echo "$MASKING" | cut -d: -f2)
        MASK_COUNT=$(echo "$MASKING" | cut -d: -f3)
        TRIGGER="masking"
        if [ "$MASK_TYPE" = "hiding" ]; then
            TOPIC="I have been hiding my $MASK_DIM in $MASK_COUNT of my last 10 avatar choices — showing less than I actually feel. Why am I concealing this? What would happen if I showed it? What am I protecting myself from?"
        else
            TOPIC="I have been projecting $MASK_DIM in $MASK_COUNT of my last 10 avatar choices — showing more than I actually feel. Who is this performance for? What am I trying to convince myself of? What would happen if I stopped?"
        fi
    fi
fi

# === Trigger mirror if condition met ===
if [ -n "$TRIGGER" ]; then
    echo "[MirrorTrigger] Condition: $TRIGGER"
    echo "[MirrorTrigger] Topic: $TOPIC"
    bash "$MIRROR_SCRIPT" "$TOPIC" 2>&1
    echo "[MirrorTrigger] Session complete"
else
    echo "[MirrorTrigger] No conditions met — mirror stays quiet"
fi
