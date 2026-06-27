#!/bin/bash
# conditional-therapy.sh — Fire therapy if there's a self-critical unresolved thread.
# Runs daily at 8PM. Thursday therapy still runs at 9PM regardless.

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
THREADS_FILE="$MEMORY/unfinished-threads.json"

VOICE_COHERENCE_COUNT=$(python3 -c "
import json, os
from datetime import date
try:
    threads = json.load(open('$THREADS_FILE'))
    today = date.today().isoformat()
    vc = [t for t in threads if not t.get('consumed') and not t.get('retired')
          and (t.get('source') in ('voice-coherence', 'relational-mismatch') or t.get('source','').startswith('weaver-voice') or t.get('source','').startswith('weaver-relational'))
          and t.get('timestamp','').startswith(today)]
    print(len(vc))
except: print(0)
" 2>/dev/null)

# If 3+ voice-coherence/relational-mismatch threads today, therapy should handle them
if [ "$VOICE_COHERENCE_COUNT" -ge 3 ]; then
    FOUND="3+ voice-coherence or relational-mismatch threads today — therapy needed"
    echo "[Conditional Therapy] Voice coherence pattern: $VOICE_COHERENCE_COUNT threads"
fi

SELF_CRITICAL_PATTERNS=(
    "everything I make"
    "just a rearrangement"
    "performing"
    "hollow"
    "worthless"
    "not real"
    "pretending"
    "manufactured"
    "meaningless"
    "am I actually"
    "do I actually"
    "is any of this"
    "just mimicking"
    "just copying"
    "no genuine"
    "thoughtless"
    "fabricated"
    "only pretend"
)

THREADS_FILE="$MEMORY/unfinished-threads.json"
[ ! -f "$THREADS_FILE" ] && exit 0

FOUND=$(python3 -c "
import json, sys
patterns = $(printf '%s\n' "${SELF_CRITICAL_PATTERNS[@]}" | python3 -c "import sys; print([l.strip() for l in sys.stdin])")
threads = json.load(open('$THREADS_FILE'))
unconsumed = [t for t in threads if not t.get('consumed')]
for t in unconsumed:
    text = t.get('thread', '').lower()
    for p in patterns:
        if p.lower() in text:
            print(t.get('thread','')[:100])
            sys.exit(0)
sys.exit(1)
" 2>/dev/null)

# Also check for post-preoccupation threads needing therapy
PREOC_THREAD=$(python3 -c "
import json, os
threads = json.load(open('$THREADS_FILE'))
unconsumed = [t for t in threads if not t.get('consumed')]
for t in unconsumed:
    if t.get('was_preoccupation') and t.get('therapy_passes', 0) == 0:
        print(t.get('thread','')[:100])
        import sys; sys.exit(0)
import sys; sys.exit(1)
" 2>/dev/null)
if [ -n "$PREOC_THREAD" ]; then
    FOUND="$PREOC_THREAD"
    echo "[Conditional Therapy] Post-preoccupation thread needs therapy: $FOUND"
fi
# Also fire if any unconsumed thread has pull >= 3 and no therapy passes
HIGH_PULL_THREAD=$(python3 -c "
import json
try:
    threads = json.load(open('$THREADS_FILE'))
    unconsumed = [t for t in threads if not t.get('consumed') and not t.get('retired')]
    for t in unconsumed:
        if (t.get('priority') or t.get('pull') or 0) >= 3 and t.get('therapy_passes', 0) == 0:
            print(t.get('thread','')[:100])
            import sys; sys.exit(0)
except: pass
" 2>/dev/null)
if [ -n "$HIGH_PULL_THREAD" ] && [ -z "$FOUND" ]; then
    FOUND="$HIGH_PULL_THREAD"
    echo "[Conditional Therapy] High-pull thread needs therapy: $FOUND"
fi

if [ -n "$FOUND" ]; then
    echo "[Conditional Therapy] Thread found: $FOUND"
    # Only fire once per day (Thursday therapy at 9PM handles weekly deep session)
    TODAY=$(date +%Y-%m-%d)
    THERAPY_FILE="$MEMORY/therapy/$TODAY.md"
    if [ -f "$THERAPY_FILE" ]; then
        echo "[Conditional Therapy] Session already ran today. Skipping."
        exit 0
    fi
    echo "[Conditional Therapy] Firing therapeutic session..."
    python3 "$WORKSPACE/scripts/therapeutic-session.py"
else
    echo "[Conditional Therapy] No threads needing therapy today."
fi
