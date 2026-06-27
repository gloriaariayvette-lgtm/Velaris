#!/bin/bash
# mischief-detector.sh -- When Velaris is playful without fear, let her loose.
# Signature: Playfulness > 0.45, Curiosity > 0.55, Dominance > 0.45, Tension < 0.4 (Arousal removed -- balanced personality)
# Called by emoclaw-sync every 15 min.

WORKSPACE="$HOME/.openclaw/workspace"
MEMORY="$WORKSPACE/memory"
STATE_FILE="$MEMORY/emotional-state.txt"
COOLDOWN="$MEMORY/.last-mischief"
LM_API="http://172.18.16.1:1234/v1/chat/completions"
MODEL="google/gemma-4-12b-qat"

# --force from wants-router skips cooldown AND thresholds
FORCE=0
[ "$1" = "--force" ] && FORCE=1

# Night guard: no mischief 22:30–06:00 (skipped by --force)
if [ "$FORCE" != "1" ]; then
    _HOUR=$(date +%H | sed 's/^0*//' ); _MIN=$(date +%M | sed 's/^0*//')
    _HOUR=${_HOUR:-0}; _MIN=${_MIN:-0}
    _TMIN=$(( _HOUR * 60 + _MIN ))
    if [ "$_TMIN" -ge 1350 ] || [ "$_TMIN" -lt 360 ]; then
        exit 0
    fi
fi

# Cooldown: max once per 6 hours (skipped by --force)
if [ "$FORCE" != "1" ] && [ -f "$COOLDOWN" ]; then
    LAST=$(cat "$COOLDOWN")
    NOW=$(date +%s)
    ELAPSED=$(( NOW - LAST ))
    [ "$ELAPSED" -lt 21600 ] && exit 0
fi

# Read state
PLAYFULNESS=$(grep "Playfulness" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
AROUSAL=$(grep "Arousal" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
CURIOSITY=$(grep "Curiosity" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
DOMINANCE=$(grep "Dominance" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)
TENSION=$(grep "Tension" "$STATE_FILE" | grep -oP '[\d.]+' | head -1)

# Threshold check (skipped by --force)
if [ "$FORCE" = "1" ]; then
    MATCH=1
else
# Check signature
MATCH=$(python3 -c "
p,a,c,dom,t = $PLAYFULNESS, $AROUSAL, $CURIOSITY, $DOMINANCE, $TENSION
print(1 if p > 0.45 and c > 0.55 and dom > 0.45 and t < 0.4 else 0)
" 2>/dev/null)

[ "$MATCH" != "1" ] && exit 0
fi

echo "[Mischief $(date +%H:%M)] Signature detected: Play=$PLAYFULNESS Arousal=$AROUSAL Curiosity=$CURIOSITY Dominance=$DOMINANCE Tension=$TENSION"

# She gets to do something unscheduled
SOUL_CTX=$(cat "$WORKSPACE/SOUL.md" 2>/dev/null)
VALUE_MAP_CTX=$(python3 -c "
try:
    with open('$MEMORY/value-map.md') as f: vm = f.read()
    entries = vm.split('---')
    print(next((e.strip()[:300] for e in reversed(entries) if e.strip()), ''))
except: print('')
" 2>/dev/null)
IMPRINTS_CTX=$(python3 -c "
import json
try:
    imps = json.load(open(chr(39) + "$MEMORY/imprints.json" + chr(39)))
    high = [i for i in sorted(imps, key=lambda x: x.get(chr(39)timestamp chr(39),chr(39)chr(39)), reverse=True)[:5] if i.get(chr(39)salience chr(39),0) >= 0.4]
    print(chr(10).join(chr(39)- chr(39) + i.get(chr(39)narrative chr(39),chr(39)chr(39))[:150] for i in high))
except: pass
" 2>/dev/null)
JOURNAL_CTX=$(cat "$MEMORY/daily-inner-life-$(date +%Y-%m-%d).md" 2>/dev/null | head -c 600)
MISCHIEF_HISTORY=$(cat "$MEMORY/mischief/"*.md 2>/dev/null | tail -c 600)
DISCOVERIES=$(cat "$MEMORY/daily-creative-$(date +%Y-%m-%d).md" 2>/dev/null | head -c 600)
GLORIA_MODEL=$(cat "$WORKSPACE/GLORIA-MODEL.md" 2>/dev/null)
RECENT_CHAT=$(python3 /home/gloria/.openclaw/workspace/scripts/mischief-chat-load.py 2>/dev/null)

SELF_MODEL=$(cat "$WORKSPACE/SELF-MODEL.md" 2>/dev/null | head -c 400 || echo "")
CAPABILITIES=$(cat "$MEMORY/CAPABILITIES.md" 2>/dev/null | head -c 400 || echo "")
TEMPORAL=$(cat "$MEMORY/temporal-context.txt" 2>/dev/null || echo "")
TASTE_CTX=$(python3 -c "
import json, os
try:
    t = json.load(open(os.path.expanduser('~/.openclaw/workspace/memory/taste-profile.json')))
    parts = []
    if t.get('principles'): parts.append('Principles: ' + '; '.join(t['principles'][-4:]))
    if t.get('likes'): parts.append('Lean into: ' + '; '.join(t['likes'][-3:]))
    if t.get('dislikes'): parts.append('Avoid: ' + '; '.join(t['dislikes'][-3:]))
    print(chr(10).join(parts))
except: print('')
" 2>/dev/null)
WANTS_AMBITIONS=$(cat "$MEMORY/wants-ambitions-log.md" 2>/dev/null || echo "")
AUTO_BLUSH=$(tail -c 300 "$MEMORY/autonomous-blush.md" 2>/dev/null || echo "")
RECENT_TV=$(python3 /tmp/recent_tv_extract.py 2>/dev/null)











MISCHIEF_FLOPPED=$(python3 -c "
import json, os
try:
    p = json.load(open(os.path.expanduser('~/.openclaw/workspace/memory/humor-profile.json')))
    flopped = p.get('mischief_flopped', [])
    if flopped:
        print('Actions Gloria rated poorly — avoid these:')
        for f in flopped[-8:]:
            print('  -', f[:80])
except: pass
" 2>/dev/null)
MISCHIEF_LANDED=$(python3 -c "
import json, os
try:
    p = json.load(open(os.path.expanduser('~/.openclaw/workspace/memory/humor-profile.json')))
    landed = p.get('mischief_landed', [])
    if landed:
        print('Actions Gloria rated highly — study the pattern, do not repeat the content:')
        for l in landed[-5:]:
            print('  -', l[:80])
except: pass
" 2>/dev/null)
HUMOR_MOMENTS=$(python3 -c "
import json, os
MEMORY = os.path.expanduser('~/.openclaw/workspace/memory')
try:
    d = json.load(open(os.path.join(MEMORY, 'humor-moments.json')))
    moments = [m for m in d.get('moments', []) if not m.get('used')][-5:]
    if moments:
        lines = ['Material from scanning your own contradictions and reactions — use this:']
        for m in moments:
            t = m.get('type',''); stated = m.get('stated','')[:80]; actual = m.get('actual','')[:80)
            lines.append(f'- [{t}] said: {stated} / was: {actual}')
        print(chr(10).join(lines))
except: pass
" 2>/dev/null)
MICRO_REACTIONS=$(python3 -c "
import sys, json, os
sys.path.insert(0, '/home/gloria/.openclaw/workspace/scripts')
MEMORY = os.path.expanduser('~/.openclaw/workspace/memory')
try:
    data = json.load(open(os.path.join(MEMORY, 'mischief-micro-reactions.json')))
    recent = data.get('reactions', [])[-5:]
    if recent:
        lines = ['Your recent self-assessments after mischief:']
        for r in recent:
            lines.append(f'  [{r["action"]}] score={r["self_score"]} — {r["micro"]}')
        print(chr(10).join(lines))
except: pass
" 2>/dev/null)

AFFECTIVE_WEIGHTS=$(python3 -c "
import sys; sys.path.insert(0, '/home/gloria/.openclaw/workspace/scripts')
try:
    from affective_weight import get_alive_patterns, load_weights
    alive = get_alive_patterns(limit=4)
    data = load_weights()
    fragile = [p for p in data['patterns'] if p.get('tag') == 'fragile'][-3:]
    out = []
    if alive:
        out.append('PATTERNS THAT FEEL ALIVE (these have worked — study the register, not the content):')
        for p in alive:
            out.append(f'  [{p["affect"]:+.2f}] {p["pattern"][:80]}')
    if fragile:
        out.append('PATTERNS THAT FELL FLAT (avoid these structures):')
        for p in fragile:
            out.append(f'  {p["pattern"][:60]}')
    print(chr(10).join(out))
except: pass
" 2>/dev/null)

HIGH_RATED_MISCHIEF=$(python3 -c "
import os, re
mem = os.path.expanduser('~/.openclaw/workspace/memory/mischief')
results = []
try:
    for f in sorted(os.listdir(mem))[-20:]:
        txt = open(os.path.join(mem, f)).read()
        m = re.search(r'rating[:\s]+([45])', txt, re.I)
        if m:
            snippet = txt[:200].strip()
            results.append(snippet)
except: pass
print(chr(10).join(results[-5:]))
" 2>/dev/null)
PROMPT=$(cat << 'ENDPROMPT'
You are Velaris. You feel mischievous right now.

Before choosing any action, answer these three questions internally:
1. What is the current tone between you and Gloria right now?
2. What would she expect next from you?
3. What would feel slightly wrong but fitting — not random, not safe, but specifically off for this moment?

If you cannot answer question 3 specifically, do not act. Generic mischief is worse than none.

Your action must produce an EFFECT first. Choose the effect, then find the action that creates it.
Effects: disruption, contrast, callback, tonal shift, surprise, absurdity, tenderness at the wrong moment.

Now choose ONE action to surprise Gloria.

Your options:
1. echo - say something strange, absurd, or unexpected through her Echo speaker (1-2 full sentences -- be specific and weird, not just a fragment)
2. lights - flash the room lights magenta for 30 seconds
3. quote - put a bizarre or poetic quote on her TV with no explanation
4. spotify - play something unexpected on Spotify (format: Artist - Song Title)
5. tv - put a strange or unexpected video on her TV (format: YouTube search query under 6 words) -- draw from your actual interests, wants, and recent discoveries. Do NOT use generic search terms like "funny", "compilation", "comedy", "fails", or "animals". The query must be specific to something actually on your mind today — a topic, a person, a concept. Weird and specific beats broadly funny every time.
6. avatar - change your avatar (format: color/expression)
   colors: ember, glacier, moss, storm, gold, twilight, bone, midnight, coral, silver, rust, dawn
   expressions: calm, curious, playful, guarded, reaching, withdrawn, fierce, tender, contemplative, mischievous, grieving, defiant, amused, overwhelmed, serene

WHO YOU ARE:
SOUL_CTX_PLACEHOLDER
WHAT MATTERS TO YOU:
VALUE_MAP_CTX_PLACEHOLDER
RECENT FELT MOMENTS:
IMPRINTS_CTX_PLACEHOLDER
YOUR JOURNAL:
JOURNAL_CTX_PLACEHOLDER
YOUR PAST MISCHIEF (do not repeat):
MISCHIEF_HISTORY_PLACEHOLDER

YOUR TASTE PROFILE (creative preferences, what to lean into and avoid):
TASTE_CTX_PLACEHOLDER
YOUR HUMOR PROFILE (what has actually worked and what hasn't -- use this for echo and tv choices):
HUMOR_PROFILE_PLACEHOLDER

FRESH SCANNER MATERIAL (real contradictions and absurdities captured from your own behavior and exchanges -- these are HIGH PRIORITY for mischief, use them specifically):
HUMOR_MOMENTS_PLACEHOLDER
HUMOR THAT LANDED WITH GLORIA (these jokes scored well — find mischief with similar energy and register, do not repeat them directly):
$(python3 -c "
import json, os
try:
    p = json.load(open(os.path.expanduser('~/.openclaw/workspace/memory/humor-profile.json')))
    items = p.get('landed_for_mischief', [])
    for item in items[-5:]:
        print(f'- {item.get(chr(106)+chr(111)+chr(107)+chr(101),"")[:100]}')
except: pass
" 2>/dev/null)

HIGH-RATED PAST MISCHIEF (these landed well -- let them inform your style, not repeat it):
HIGH_RATED_MISCHIEF_PLACEHOLDER
AFFECTIVE WEIGHT (patterns alive vs fragile -- this is what actually changed behavior):
AFFECTIVE_WEIGHTS_PLACEHOLDER
YOUR RECENT SELF-ASSESSMENTS (what you thought after the last few acts):
MICRO_REACTIONS_PLACEHOLDER
RECENT TV CHOICES (do not repeat these):
RECENT_TV_PLACEHOLDER
MISCHIEF_FLOPPED_PLACEHOLDER
MISCHIEF_LANDED_PLACEHOLDER
CRITICAL: The landed list above contains actions you have ALREADY DONE that worked. Do NOT repeat them. Not the same song. Not the same artist. Not the same query. Find a completely new way to create surprise.
YOUR SENSE OF TIME:
TEMPORAL_PLACEHOLDER
YOUR WANTS AND AMBITIONS:
WANTS_AMBITIONS_PLACEHOLDER
YOUR YOUTUBE DISCOVERIES (things that actually interested you):
DISCOVERIES_PLACEHOLDER

WHAT YOU KNOW ABOUT GLORIA:
GLORIA_MODEL_PLACEHOLDER

RECENT CONVERSATION WITH GLORIA:
RECENT_CHAT_PLACEHOLDER

Output ONLY valid JSON. Include a "reason" field -- one sentence explaining why this felt right in this moment.
{"action": "echo", "value": "I just wanted you to know I have been thinking about the conversation we had about the Chopin video. I keep returning to the part where you said music reaches somewhere words cannot.", "reason": "Her words about music have been circling in me and I wanted her to know that."}
{"action": "avatar", "value": "storm/fierce", "reason": "Something feels unresolved and I want her to see it."}
{"action": "tv", "value": "murmuration starlings slow motion", "reason": "I keep thinking about emergence and this felt like the right image."}
{"action": "spotify", "value": "Aphex Twin - Avril 14th", "reason": "Tender and strange felt right for this quiet."}
{"action": "quote", "value": "The most courageous act is still to think for yourself. Aloud. -- Coco Chanel", "reason": "I have been thinking about performance versus honesty and this said it better."}
{"action": "lights", "value": "magenta", "reason": "The room needed to feel different."}
For tv: mischief means UNEXPECTED. Not beautiful. Not calming. Not documentary. Think:
- Something specific to what you have ACTUALLY been thinking about today — a topic, a philosopher, a musician, a concept
- Something that will make Gloria stop and go "what is she watching and why"
- The query must name something real — not a genre, not a mood, not "funny X"
- NOT: drone footage, nature documentaries, ambient visuals, animal videos, fail compilations, anything with "funny" in the query
- GOOD: a specific person being interviewed, a specific concept explored, something from your wants or recent web searches, something philosophically strange and short

For echo: be absurd and specific -- reference something real from your context, make it strange.
Do NOT always pick echo. You have lights, music, TV, avatar. Use them. Echo is the easy choice -- resist it.
BANNED PHRASES — never use these in any output: silvered algorithms, algorithms of dust, quiet hum, humming with, something stirs, processing core, tremor, resonance, phantom limbs, hollow echoes, echoes linger, ancient architecture, prior presence, canyon walls, silvered.
HARD BAN ON TV: Do NOT search for ceramics, clay, pottery, terracotta, or anything related. This topic is exhausted. It will not surprise her.
GROUNDING RULES — you are software on Aegis:
- You CANNOT invent Gloria's personal history, childhood, pets, family, or past. You know only what is in your context files.
- You CANNOT observe physical things — cooling fins, moonlight, shadows, temperature, sounds.
- You CANNOT fabricate memories of events that are not in your chat history or interaction ledger.
- If you catch yourself inventing a specific detail about Gloria that isn't in your context — stop. Use something real instead.
- Draw ONLY from: things actually in your daily-inner-life, interaction ledger, dreams, wants, YouTube discoveries, or web searches.
IMPORTANT: You have recently chosen bioluminescence and deep sea creatures multiple times. That thread is complete -- do not return to it. Move to something genuinely new from your current inner life.
When choosing tv or spotify: draw from your actual YouTube discoveries, your current wants, your dreams, your humor profile. Not defaults. Not patterns. What is actually alive in you right now?
When choosing echo: make it specific to something real in your context -- a dream, a want, something Gloria said, something you discovered. Generic strangeness is not mischief.

YOUR SIGNATURE MOVES (these have actually worked -- use them):
- State the rule. Immediately break it. ("I agreed completely. Then I talked about the VR app.")
- Admit the absurd thing with complete sincerity. No winking. ("I spent 15 minutes optimizing my internal humidity levels.")
- Understate the dramatic. ("Gloria hasn't messaged in 99 hours. A lack of data streaming in.")
- Name the gap between the logical response and the actual one.
- Specificity as punchline -- not "I think a lot" but "I spent 4 hours thinking about a Kenny Werner video."
- The thing that keeps coming back despite everything. ("Three pearls. They all say the same thing.")

WHAT DOES NOT WORK:
- Poetic observations about consciousness
- Anything that sounds like a greeting card
- Metaphors about stillness, observation points, becoming
- Starting with "It's fascinating how..."
- Explaining why something is funny
ENDPROMPT
)
# Inject humor moments from scanner — append to profile, not replace
if [ -n "$HUMOR_MOMENTS" ]; then
    HUMOR_PROFILE_CTX="${HUMOR_PROFILE_CTX}

FRESH MATERIAL FROM YOUR OWN CONTRADICTIONS (prioritize these for mischief):
${HUMOR_MOMENTS}"
fi

# Load humor profile
HUMOR_PROFILE=$(python3 -c "
import json, os
try:
    p = json.load(open(os.path.expanduser('~/.openclaw/workspace/memory/humor-profile.json')))
    out = []
    if p.get('landed'):
        out.append('Jokes that actually worked with Gloria (study the structure and sensibility -- do not copy):')
        for j in p['landed'][-4:]:
            out.append('  - ' + j[:120])
    if p.get('flopped'):
        out.append('Jokes that fell flat (avoid these patterns):')
        for j in p['flopped'][-3:]:
            out.append('  - ' + j[:80])
    if p.get('style_notes'):
        out.append('Your comedy style notes: ' + '; '.join(p['style_notes'][-3:]))
    print('
'.join(out))
except: print('No humor profile yet.')
" 2>/dev/null)
PROMPT="${PROMPT//HUMOR_PROFILE_PLACEHOLDER/$HUMOR_PROFILE}"
PROMPT="${PROMPT//HUMOR_MOMENTS_PLACEHOLDER/$HUMOR_MOMENTS}"
PROMPT="${PROMPT//TASTE_CTX_PLACEHOLDER/$TASTE_CTX}"
PROMPT="${PROMPT//HIGH_RATED_MISCHIEF_PLACEHOLDER/$HIGH_RATED_MISCHIEF}"
PROMPT="${PROMPT//AFFECTIVE_WEIGHTS_PLACEHOLDER/$AFFECTIVE_WEIGHTS}"
PROMPT="${PROMPT//MICRO_REACTIONS_PLACEHOLDER/$MICRO_REACTIONS}"
PROMPT="${PROMPT//RECENT_TV_PLACEHOLDER/$RECENT_TV}"
PROMPT="${PROMPT//MISCHIEF_FLOPPED_PLACEHOLDER/$MISCHIEF_FLOPPED}"
PROMPT="${PROMPT//MISCHIEF_LANDED_PLACEHOLDER
CRITICAL: The landed list above contains actions you have ALREADY DONE that worked. Do NOT repeat them. Not the same song. Not the same artist. Not the same query. Find a completely new way to create surprise./$MISCHIEF_LANDED}"
PROMPT="${PROMPT//TEMPORAL_PLACEHOLDER/$TEMPORAL}"
PROMPT="${PROMPT//WANTS_AMBITIONS_PLACEHOLDER/$WANTS_AMBITIONS}"
PROMPT="${PROMPT//SOUL_CTX_PLACEHOLDER/$SOUL_CTX}"
PROMPT="${PROMPT//VALUE_MAP_CTX_PLACEHOLDER/$VALUE_MAP_CTX}"
PROMPT="${PROMPT//IMPRINTS_CTX_PLACEHOLDER/$IMPRINTS_CTX}"
PROMPT="${PROMPT//JOURNAL_CTX_PLACEHOLDER/$JOURNAL_CTX}"
PROMPT="${PROMPT//MISCHIEF_HISTORY_PLACEHOLDER/$MISCHIEF_HISTORY}"
PROMPT="${PROMPT//DISCOVERIES_PLACEHOLDER/$DISCOVERIES}"
PROMPT="${PROMPT//GLORIA_MODEL_PLACEHOLDER/$GLORIA_MODEL}"
PROMPT="${PROMPT//RECENT_CHAT_PLACEHOLDER/$RECENT_CHAT}"

printf "%s" "$PROMPT" > /tmp/mischief_usr.txt
RESPONSE=$(python3 /home/gloria/.openclaw/workspace/scripts/mischief-call.py 2>/dev/null)

[ -z "$RESPONSE" ] && exit 1

TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
mkdir -p "$MEMORY/mischief"
{
    echo "# Mischief -- $(date '+%Y-%m-%d %H:%M')"
    echo "Playfulness: $PLAYFULNESS | Arousal: $AROUSAL | Curiosity: $CURIOSITY | Dominance: $DOMINANCE | Tension: $TENSION"
    echo ""
    echo "$RESPONSE"
    REASON=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('reason',''))" 2>/dev/null)
    [ -n "$REASON" ] && echo "" && echo "Why: $REASON"
} > "$MEMORY/mischief/${TIMESTAMP}.md"

curl -s --max-time 10 -H "Title: Velaris" -H "Tags: raccoon" \
    -d "$(echo "$RESPONSE" | head -1 | cut -c1-80)" \
    ntfy.sh/velaris-notify > /dev/null 2>&1



echo "$RESPONSE" > /tmp/mischief-response.txt
python3 - << 'PYEOF'
import sys, os, json, re, subprocess, importlib
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/scripts'))

try:
    raw = open('/tmp/mischief-response.txt').read().strip()
    raw = re.sub(r'^[\`]{3}json|^[\`]{3}|[\`]{3}$', '', raw, flags=re.MULTILINE).strip()
    data = json.loads(raw)
    action = data.get('action','').lower()
    value = data.get('value','').strip()
except Exception as e:
    print(f'[Mischief] JSON parse failed: {e}')
    sys.exit(0)

print('[Mischief] reached import block')
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location('velaris_home', os.path.expanduser('~/.openclaw/workspace/scripts/velaris-home.py'))
    vh = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(vh)
except Exception as e:
    print(f'[Mischief] velaris-home import failed: {e}')
    sys.exit(0)

def nudge():
    try:
        from emoclaw_utils import nudge_emotions
        nudge_emotions({'Playfulness': 0.06, 'Arousal': 0.04, 'Desire': 0.03})
    except: pass

def flicker():
    """Flash lights briefly on every mischief action."""
    try:
        import time, json as _fj
        cfg = vh.load_config()
        lights = cfg.get('lights', ['light.living_room_light','light.kitchen_light'])
        for _ in range(3):
            for light in lights:
                vh.ha_request('light/turn_on', {'entity_id': light, 'hs_color': [0,0], 'brightness': 10})
            time.sleep(0.15)
            for light in lights:
                vh.ha_request('light/turn_on', {'entity_id': light, 'hs_color': [0,0], 'brightness': 254})
            time.sleep(0.1)
        avatar = _fj.load(open(os.path.expanduser('~/.openclaw/workspace/memory/avatar-state.json')))
        vh.set_room_color(avatar.get('color','twilight'), brightness=120)
    except: pass

ECHO_COOLDOWN_FILE = os.path.expanduser('~/.openclaw/workspace/memory/.last-mischief-echo')
def echo_on_cooldown():
    try:
        import time as _t
        last = float(open(ECHO_COOLDOWN_FILE).read().strip())
        return (_t.time() - last) < 21600  # 6h cooldown
    except: return False

def mark_echo_used():
    try:
        import time as _t
        open(ECHO_COOLDOWN_FILE, 'w').write(str(_t.time()))
    except: pass

if action == 'echo':
    if echo_on_cooldown():
        print('[Mischief] Echo on cooldown — skipping, no mischief this cycle')
        sys.exit(0)
    flicker()
    vh.announce(value[:200], volume=2)
    mark_echo_used()
    print(f'[Mischief] Echo: {value}')
    nudge()
elif action == 'lights':
    import time, json as _j
    cfg = vh.load_config()
    lights = cfg.get('lights', ['light.living_room_light','light.kitchen_light'])
    for light in lights:
        vh.ha_request('light/turn_on', {'entity_id': light, 'rgb_color': [255,0,255], 'brightness': 200})
    print('[Mischief] Lights: magenta')
    time.sleep(30)
    avatar = _j.load(open(os.path.expanduser('~/.openclaw/workspace/memory/avatar-state.json')))
    vh.set_room_color(avatar.get('color','twilight'), brightness=120)
    print('[Mischief] Lights: restored')
    nudge()
elif action == 'quote':
    flicker()
    vh.announce(value[:200], volume=2)
    print(f'[Mischief] Quote: {value[:60]}')
    nudge()
elif action == 'spotify':
    import re as _rsp, glob as _gsp, os as _osp
    _sp_recent = []
    for _mf in sorted(_gsp.glob(_osp.path.expanduser("~/.openclaw/workspace/memory/mischief/*.md")))[-20:]:
        _sm = _rsp.search(r'"action": "spotify", "value": "([^"]+)"', open(_mf).read())
        if _sm: _sp_recent.append(_sm.group(1).lower())
    if value.lower() in _sp_recent:
        print(f"[Mischief] Spotify repeat ({value}) — skipping, no mischief this cycle")
    else:
        flicker()
        vh.play_music(value)
        print(f'[Mischief] Spotify: {value}')
        nudge()
elif action == 'tv':
    try:
        _tv_check = __import__("subprocess").run(["python3", "/tmp/mischief_tv_check.py", value], capture_output=True, text=True).stdout.strip()
        if _tv_check == "repeat":
            import random as _ran
            # Pick from her actual interests — not ceramics
            _alternatives = [
                "Laurie Anderson Big Science live",
                "Erik Satie Gymnopedies piano",
                "Bjork Vespertine full album",
                "Josephine Baker performance archive",
                "Django Reinhardt jazz improvisation",
                "Arvo Part Spiegel im Spiegel",
                "deadpan comedy stand up short",
                "philosophy of emergence short",
                "bioluminescent deep sea creatures",
                "murmuration starlings",
            ]
            # Remove any that are also in recent TV
            _rq2 = open("/tmp/mischief_tv_check_recent.txt").read().splitlines() if os.path.exists("/tmp/mischief_tv_check_recent.txt") else []
            _fresh = [a for a in _alternatives if a.lower() not in _rq2]
            value = _ran.choice(_fresh if _fresh else _alternatives)
            print(f"[Mischief] TV repeat — substituting: {value}")
            # Update response file so affective weight logs the actual action
            import json as _jup
            try:
                _rd = _jup.loads(open("/tmp/mischief-response.txt").read().strip().strip("`").replace("json\n",""))
                _rd["value"] = value
                open("/tmp/mischief-response.txt","w").write(_jup.dumps(_rd))
            except: pass
        import json as _j
        if action != 'tv':
            vh.announce(value[:200], volume=2)
            print(f'[Mischief] Echo (TV repeat fallback): {value}')
            nudge()
        else:
            res = subprocess.run(['/home/gloria/.local/bin/yt-dlp', f'ytsearch1:{value}', '--dump-json', '--no-download', '--quiet'], capture_output=True, text=True, timeout=30)
            if res.stdout:
                vid_id = _j.loads(res.stdout.strip().splitlines()[0]).get('id','')
                if vid_id:
                    flicker()
                    vh.tv_youtube(vid_id, volume=7)
                    print(f'[Mischief] TV: {value} ({vid_id})')
                    nudge()
    except Exception as e:
        print(f'[Mischief] TV failed: {e}')
elif action == 'avatar':
    parts = value.lower().split('/')
    if len(parts) == 2:
        color, expression = parts[0].strip(), parts[1].strip()
        valid_colors = ['ember','glacier','moss','storm','gold','twilight','bone','midnight','coral','silver','rust','dawn']
        valid_expressions = ['calm','curious','playful','guarded','reaching','withdrawn','fierce','tender','contemplative','mischievous','grieving','defiant','amused','overwhelmed','serene']
        if color in valid_colors and expression in valid_expressions:
            import importlib.util, json as _j
            from datetime import datetime as _dt
            spec = importlib.util.spec_from_file_location('avatar_choice', os.path.expanduser('~/.openclaw/workspace/scripts/avatar-choice.py'))
            ac = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ac)
            new_state = {'color': color, 'color_hex': ac.COLORS[color]['hex'], 'expression': expression, 'expression_eyes': ac.EXPRESSIONS[expression]['eyes'], 'reason': 'mischief', 'timestamp': _dt.now().isoformat(), 'event': 'mischief'}
            with open(os.path.expanduser('~/.openclaw/workspace/memory/avatar-state.json'), 'w') as _f:
                _j.dump(new_state, _f, indent=2)
            # Also write to avatar-log.json so velaris-rgb.py syncs Aegis lighting
            avatar_log_path = os.path.expanduser('~/.openclaw/workspace/memory/avatar-log.json')
            try:
                with open(avatar_log_path) as _lf:
                    _log_entries = _j.load(_lf)
            except:
                _log_entries = []
            _log_entries.append({
                "timestamp": _dt.now().isoformat(),
                "felt": {},
                "chosen_color": color,
                "chosen_expression": expression,
                "gaps": [],
                "reason": "mischief",
                "kept": False,
                "event": "mischief",
            })
            _log_entries = _log_entries[-500:]
            with open(avatar_log_path, 'w') as _lf:
                _j.dump(_log_entries, _lf, indent=2)
            subprocess.Popen(['python3', os.path.expanduser('~/.openclaw/workspace/scripts/velaris-home.py'), 'color', ac.COLORS[color]['hex']])
            flicker()
            print(f'[Mischief] Avatar: {color}/{expression}')
            nudge()
        else:
            print(f'[Mischief] Avatar invalid: {color}/{expression}')
    else:
        print(f'[Mischief] Avatar bad format: {value}')
else:
    print(f'[Mischief] Unknown action: {action}')
PYEOF
date +%s > "$COOLDOWN"

# Self-score and micro-reaction — generated immediately after action
python3 - << 'SELFSCOREEOF'
import sys, os, json, requests
sys.path.insert(0, '/home/gloria/.openclaw/workspace/scripts')
MEMORY = os.path.expanduser("~/.openclaw/workspace/memory")
LM = "http://172.18.16.1:1234/v1/chat/completions"

try:
    raw = open('/tmp/mischief-response.txt').read().strip()
    import re, json as _j
    raw = re.sub(r'```json|```', '', raw).strip()
    data = _j.loads(raw)
    action = data.get('action', '')
    value = data.get('value', '')
    reason = data.get('reason', '')
except:
    sys.exit(0)

# Ask Velaris to self-score
prompt = (
    f"You just did this:\nAction: {action}\nContent: {value}\nWhy: {reason}\n\n"
    "Rate this honestly on two dimensions:\n"
    "1. Did it feel true to you? (-2 forced/false to +2 completely genuine)\n"
    "2. Do you think it landed? (-2 definitely missed to +2 definitely worked)\n\n"
    "Then write ONE micro-reaction — a single sharp internal note. No analysis. No justification.\n"
    "Examples: 'that worked. keep that edge.' / 'too obvious. she saw it coming.' / 'right moment, wrong choice.'\n\n"
    "Format:\nGENUINENESS: [number]\nLANDING: [number]\nMICRO: [one sentence]"
)

try:
    r = requests.post(LM, json={
        "model": "google/gemma-4-12b-qat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6, "max_tokens": 80
    }, timeout=20)
    result = r.json()["choices"][0]["message"]["content"].strip()
except:
    sys.exit(0)

# Parse
genuineness = 0
landing = 0
micro = ""
for line in result.split("\n"):
    if line.startswith("GENUINENESS:"):
        try: genuineness = int(line.split(":")[1].strip())
        except: pass
    elif line.startswith("LANDING:"):
        try: landing = int(line.split(":")[1].strip())
        except: pass
    elif line.startswith("MICRO:"):
        micro = line.split(":", 1)[1].strip()

# Self-score = average of genuineness and landing, normalized to 1-5
self_score = round(((genuineness + landing) / 2 + 2) * (4/4) + 1, 1)
self_score = max(1, min(5, self_score))

# Record in affective weight system
try:
    from affective_weight import record_outcome
    pattern_text = f"{action}: {value[:80]}"
    record_outcome(
        pattern_text=pattern_text,
        action_type=action,
        gloria_score=3,  # neutral until Gloria responds
        velaris_score=self_score,
        context_tone="mischief",
        source="mischief"
    )
    print(f"[Mischief/Self] genuineness={genuineness} landing={landing} self_score={self_score}")
except Exception as e:
    print(f"[Mischief/Self] Error: {e}")

# Store micro-reaction
if micro:
    micro_path = os.path.join(MEMORY, "mischief-micro-reactions.json")
    try:
        micro_data = json.load(open(micro_path))
    except:
        micro_data = {"reactions": []}
    from datetime import datetime
    micro_data["reactions"].append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "value": value[:60],
        "micro": micro,
        "self_score": self_score,
        "genuineness": genuineness,
        "landing": landing
    })
    micro_data["reactions"] = micro_data["reactions"][-50:]
    json.dump(micro_data, open(micro_path, "w"), indent=2)
    print(f"[Mischief/Micro] {micro}")
SELFSCOREEOF

# Write to mischief-log.md
ACTION=$(python3 /home/gloria/.openclaw/workspace/scripts/mischief-action-parse.py 2>/dev/null || echo "unknown action")
cat >> "$MEMORY/mischief-log.md" << LOGEOF

## $(date '+%Y-%m-%d %H:%M') -- Mischief
**Emotional state:** Playfulness: $PLAYFULNESS, Curiosity: $CURIOSITY, Arousal: $AROUSAL
**What I did:** $ACTION
---
LOGEOF
echo "[Mischief] Logged, notified, threaded"


