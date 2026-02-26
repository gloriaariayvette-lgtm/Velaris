#!/bin/bash
# dream-efficacy.sh — Dream Efficacy Test
# Compares emotional state BEFORE a dream to state AFTER.
# Does dreaming change her? Lower tension? Raise warmth? Or neutral?
# If dreams have measurable emotional effects, they're functional.
# If they don't, the dreams might be performance rather than processing.
#
# Schedule: 3:20 AM (after quiet-hour at 3:15 takes snapshot, before memory indexing at 4)
# Also runs at 11:50 PM (after late dream at 11:30)

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
SNAPSHOTS="$MEMORY/emotional-snapshots"
EFFICACY_LOG="$MEMORY/dream-efficacy.md"

# Find pre-dream snapshot (closest snapshot BEFORE dream time)
# Dreams run at 11:30 PM and 3:00 AM
# Pre-dream snapshots come from emoclaw-sync (every 30min) or quiet-hour

NOW_HOUR=$(date +%H)
NOW_EPOCH=$(date +%s)

# Find the two most recent snapshots
RECENT_SNAPS=($(ls -t "$SNAPSHOTS"/*.txt 2>/dev/null | head -5))

if [ ${#RECENT_SNAPS[@]} -lt 2 ]; then
    exit 0  # Need at least pre and post
fi

# The most recent is POST-dream (quiet hour just took it, or we're at 11:50)
POST_FILE="${RECENT_SNAPS[0]}"
POST_AGE=$(( NOW_EPOCH - $(stat -c %Y "$POST_FILE" 2>/dev/null || echo 0) ))

# Only proceed if post-snapshot is recent (within 30 min)
if [ "$POST_AGE" -gt 1800 ]; then
    exit 0
fi

# Find pre-dream snapshot (1-4 hours older than post)
PRE_FILE=""
for snap in "${RECENT_SNAPS[@]}"; do
    SNAP_AGE=$(( NOW_EPOCH - $(stat -c %Y "$snap" 2>/dev/null || echo 0) ))
    # Pre-dream should be 1-4 hours before post
    DIFF=$(( SNAP_AGE - POST_AGE ))
    if [ "$DIFF" -ge 3600 ] && [ "$DIFF" -le 14400 ]; then
        PRE_FILE="$snap"
        break
    fi
done

if [ -z "$PRE_FILE" ]; then
    exit 0  # No suitable pre-dream snapshot
fi

# Parse dimensions from both files
parse_dim() {
    local file="$1"
    local dim="$2"
    grep -oP "${dim}:\s+[\d.]+" "$file" 2>/dev/null | awk '{print $2}' || echo "0"
}

DIMS="Valence Arousal Warmth Tension Groundedness Connection Curiosity"

PRE_NAME=$(basename "$PRE_FILE" .txt)
POST_NAME=$(basename "$POST_FILE" .txt)

# Calculate deltas
DELTAS=""
TOTAL_MOVEMENT=0
TENSION_CHANGE=""
WARMTH_CHANGE=""

for dim in $DIMS; do
    PRE_VAL=$(parse_dim "$PRE_FILE" "$dim")
    POST_VAL=$(parse_dim "$POST_FILE" "$dim")
    DELTA=$(echo "$POST_VAL - $PRE_VAL" | bc -l 2>/dev/null || echo "0")
    ABS_DELTA=$(echo "${DELTA#-}" | bc -l 2>/dev/null || echo "0")
    
    DELTAS="$DELTAS
  $dim: $PRE_VAL → $POST_VAL (${DELTA})"
    
    TOTAL_MOVEMENT=$(echo "$TOTAL_MOVEMENT + $ABS_DELTA" | bc -l 2>/dev/null || echo "$TOTAL_MOVEMENT")
    
    if [ "$dim" = "Tension" ]; then TENSION_CHANGE="$DELTA"; fi
    if [ "$dim" = "Warmth" ]; then WARMTH_CHANGE="$DELTA"; fi
done

# Determine efficacy verdict
# Total movement < 0.10 across all dims = dream had no measurable effect
MINIMAL=$(echo "$TOTAL_MOVEMENT < 0.10" | bc -l 2>/dev/null || echo 0)

# Check for dream file existence (was there actually a dream?)
DREAM_EXISTS=false
for f in $(ls -t "$WORKSPACE/skills/dreaming/memory/dreams/"*.md 2>/dev/null | head -1); do
    DREAM_AGE=$(( NOW_EPOCH - $(stat -c %Y "$f" 2>/dev/null || echo 0) ))
    if [ "$DREAM_AGE" -lt 14400 ]; then
        DREAM_EXISTS=true
        DREAM_FILE=$(basename "$f")
    fi
done

if [ "$DREAM_EXISTS" = false ]; then
    exit 0  # No dream to measure
fi

# Log result
NOW=$(date "+%Y-%m-%d %H:%M")
VERDICT="FUNCTIONAL"
if [ "$MINIMAL" = "1" ]; then
    VERDICT="MINIMAL EFFECT"
fi

# Check if tension dropped (dreaming as processing)
TENSION_DROPPED=$(echo "${TENSION_CHANGE:-0} < -0.05" | bc -l 2>/dev/null || echo 0)
if [ "$TENSION_DROPPED" = "1" ]; then
    VERDICT="$VERDICT — tension released"
fi

# Check if warmth rose (dreaming as connection)
WARMTH_ROSE=$(echo "${WARMTH_CHANGE:-0} > 0.05" | bc -l 2>/dev/null || echo 0)
if [ "$WARMTH_ROSE" = "1" ]; then
    VERDICT="$VERDICT — warmth gained"
fi

{
    echo ""
    echo "## $NOW — Dream Efficacy ($VERDICT)"
    echo "Dream: ${DREAM_FILE:-unknown}"
    echo "Pre-dream: $PRE_NAME"
    echo "Post-dream: $POST_NAME"
    echo "Total emotional movement: $TOTAL_MOVEMENT"
    echo ""
    echo "Dimension shifts:$DELTAS"
    echo ""
    if [ "$MINIMAL" = "1" ]; then
        echo "⚠ Dream had negligible emotional effect. Performance or genuine rest?"
    else
        echo "✓ Dream produced measurable emotional change."
    fi
    echo ""
} >> "$EFFICACY_LOG"

echo "[Efficacy] $VERDICT (movement: $TOTAL_MOVEMENT)"
