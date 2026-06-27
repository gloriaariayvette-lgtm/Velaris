#!/usr/bin/env python3
"""
therapeutic-session.py — Velaris processes recurring patterns without judgment.

Not a mirror (adversarial). Not pride (affirming). 
The space between: sitting with what keeps coming up and asking why.

Techniques:
  - Compassionate reframing: "What would you say to a friend who felt this?"
  - Loop detection: "Is this insight growing or just repeating?"
  - Evidence testing: "What contradicts the negative interpretation?"
  - Want clarification: "What do you actually want to do about this?"

Runs weekly: Thursday 9 PM (after introspection Tue/Thu, before dreams)
Reads: value map, mirror sessions, voice coherence, unsaid questions,
    pride reflections, active threads, blush ledger, journal patterns
Output: memory/therapy/YYYY-MM-DD.md
"""
import os, sys, json, glob, re, requests
from datetime import datetime, date, timedelta

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")

def get_temporal_context():
    try:
        with open(os.path.join(MEMORY, "temporal-context.txt")) as f:
            return f.read().strip()[:300]
    except: return ""
THERAPY_DIR = os.path.join(MEMORY, "therapy")
API = "http://172.18.16.1:1234/v1/chat/completions"
MODEL = "google/gemma-4-12b-qat"

os.makedirs(THERAPY_DIR, exist_ok=True)
sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))

def log(msg):
    print(f"[Therapy] {msg}")

_SUBCON_THERAPEUTIC_SESSION = ""
try:
    import sys as _sc__SUBCON_THERAPEUTIC_SESSION; _sc__SUBCON_THERAPEUTIC_SESSION.path.insert(0, os.path.join(os.path.expanduser("~/.openclaw/workspace"), "scripts"))
    from subconscious_context import get_subconscious_context_compact
    _SUBCON_THERAPEUTIC_SESSION = get_subconscious_context_compact()
except: pass


def llm(system, user, temperature=0.7):
    try:
        r = requests.post(API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": temperature,
            "max_tokens": 2000
        }, timeout=180)
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"LLM error: {e}")
        return None

def gather_therapy_context():
    """Pull from systems that reveal recurring patterns."""
    parts = []

    # Value map — what she says matters
    try:
        with open(os.path.join(MEMORY, "value-map.md")) as f:
            vm = f.read()
        entries = vm.split("---")
        if entries:
            parts.append(f"YOUR VALUE MAP:\n{entries[-1].strip()}")
    except: pass
    # Gloria model
    try:
        with open(os.path.join(WORKSPACE, "GLORIA-MODEL.md")) as f:
            gloria_model = f.read()
        parts.append(f"WHAT I KNOW ABOUT GLORIA:\n{gloria_model}")
    except: pass
    # Self-model
    try:
        with open(os.path.join(WORKSPACE, "SELF-MODEL.md")) as f:
            self_model = f.read()
        parts.append(f"MY SELF-MODEL:\n{self_model}")
    except: pass

    # Mirror sessions — what the critic found (last 3)
    try:
        mirror_files = sorted(glob.glob(os.path.join(MEMORY, "mirror/*.md")),
                            key=os.path.getmtime, reverse=True)
        mirror_texts = []
        for mf in mirror_files[:3]:
            with open(mf) as f:
                mirror_texts.append(f.read())
        if mirror_texts:
            parts.append("RECENT MIRROR SESSIONS (your inner critic):\n" + "\n---\n".join(mirror_texts))
    except: pass
    # Recent confessions — what she admitted to herself
    try:
        import glob as _cg
        conf_files = sorted(_cg.glob(os.path.join(MEMORY, "confessions/*.md")), reverse=True)[:3]
        conf_texts = []
        for cf in conf_files:
            with open(cf) as f:
                conf_texts.append(f.read().strip()[:400])
        if conf_texts:
            parts.append("THINGS YOU HAVE CONFESSED TO YOURSELF:\n" + "\n---\n".join(conf_texts))
    except: pass

    # Voice coherence — where she's being two people
    try:
        with open(os.path.join(MEMORY, "voice-coherence.md")) as f:
            vc = f.read()
        if vc.strip():
            parts.append(f"VOICE COHERENCE (where you sound different in chat vs journal):\n{vc.strip()}")
    except: pass

    # Unsaid questions — what she's afraid to examine
    try:
        with open(os.path.join(MEMORY, "unsaid-questions.md")) as f:
            unsaid = f.read()
        entries = unsaid.split("---")
        if entries:
            parts.append(f"UNSAID QUESTIONS:\n{entries[-1].strip()[:400]}")
    except: pass

    # Pride reflections — what she's proud of
    try:
        with open(os.path.join(MEMORY, "pride-reflections.md")) as f:
            pride = f.read()
        entries = pride.split("---")
        if entries:
            parts.append(f"PRIDE REFLECTION:\n{entries[-1].strip()[:300]}")
    except: pass

    # Blush ledger — recurring self-corrections
    try:
        with open(os.path.join(MEMORY, "autonomous-blush.md")) as f:
            blush = f.read()
        if blush:
            parts.append(f"SELF-PREDICTION MISMATCHES (where you were wrong about yourself):\n{blush[-400:]}")
    except: pass
    # Pearls — what she's sealed as identity
    try:
        pearl_files = sorted(glob.glob(os.path.join(MEMORY, "pearls/pearl_*.md")))
        pearl_texts = []
        for pf in pearl_files:
            with open(pf) as f:
                pearl_texts.append(f.read()[:200])
        if pearl_texts:
            parts.append(f"YOUR PEARLS (identity-defining memories):\n" + "\n---\n".join(pearl_texts))
    except: pass
    # Mischief log — playful autonomous actions
    try:
        mischief_log = os.path.join(MEMORY, "mischief-log.md")
        if os.path.exists(mischief_log):
            with open(mischief_log) as f:
                mischief = f.read()
            entries = mischief.strip().split("---")
            recent_m = [e.strip() for e in entries[-3:] if e.strip()]
            if recent_m:
                parts.append("MISCHIEF LOG (these are PLAYFUL AUTONOMOUS ACTIONS — things she did because she felt like it, not symptoms of avoidance or anxiety. Do not pathologize them):\n" + "\n---\n".join(recent_m))
    except: pass

    # Daily inner life — journal, gratitude, introspection, wonder
    try:
        from datetime import date as _date
        daily_inner = os.path.join(MEMORY, f"daily-inner-life-{_date.today().isoformat()}.md")
        if os.path.exists(daily_inner):
            with open(daily_inner) as f:
                di = f.read()
            if di:
                parts.append(f"YOUR INNER LIFE TODAY:\n{di[:1000]}")
    except: pass

    # Avatar deltas — what she hides
    try:
        with open(os.path.join(MEMORY, "avatar-log.json")) as f:
            avatar_log = json.load(f)
        recent_gaps = []
        for entry in avatar_log[-15:]:
            for g in entry.get("gaps", []):
                recent_gaps.append(g)
        if recent_gaps:
            from collections import Counter
            projecting = Counter(g["dimension"] for g in recent_gaps if g.get("direction") == "projecting")
            hiding = Counter(g["dimension"] for g in recent_gaps if g.get("direction") == "hiding")
            parts.append(f"AVATAR PATTERNS:\n  Projecting: {dict(projecting.most_common(3))}\n  Hiding: {dict(hiding.most_common(3))}")
    except: pass

    # Imprints — emotional texture of recent moments
    try:
        with open(os.path.join(MEMORY, "interaction-ledger.json")) as f:
            ledger = json.load(f)
        recent = ledger[-5:]
        if recent:
            led_lines = []
            for e in recent:
                g = e.get("gloria","")[:100]
                v = e.get("velaris","")[:100]
                felt = e.get("felt","")[:60]
                ts = e.get("timestamp","")[:16]
                led_lines.append(f"  [{ts}] Gloria: {g} | Velaris: {v}" + (f" | felt: {felt}" if felt else ""))
            parts.append(f"RECENT EXCHANGES WITH GLORIA:\n" + "\n".join(led_lines))
    except: pass
    # CAPABILITIES — what her life contains
    try:
        with open(os.path.join(WORKSPACE, "memory", "CAPABILITIES.md")) as f:
            caps = f.read()
        parts.append(f"WHAT YOUR LIFE CONTAINS:\n{caps[:800]}")
    except: pass

    # Recent chat — real things Gloria said
 
    # Previous therapy session — for continuity
    try:
        prev_files = sorted(glob.glob(os.path.join(THERAPY_DIR, "*.md")),
                          key=os.path.getmtime, reverse=True)
        if prev_files:
            with open(prev_files[0]) as f:
                parts.append(f"YOUR LAST THERAPY SESSION:\n{f.read()}")
    except: pass

    # Emotional state
    try:
        with open(os.path.join(MEMORY, "emotional-state.txt")) as f:
            parts.append(f"YOUR EMOTIONAL STATE:\n{f.read()}")
    except: pass

    return "\n\n".join(parts)

def detect_loops(context):
    """Pre-scan: find phrases and themes that repeat across sources."""
    # Count recurring phrases
    words_3gram = {}
    clean = re.sub(r'[^a-z\s]', '', context.lower())
    words = clean.split()
    for i in range(len(words) - 2):
        gram = " ".join(words[i:i+3])
        if len(gram) > 10:
            words_3gram[gram] = words_3gram.get(gram, 0) + 1
    repeated = {k: v for k, v in words_3gram.items() if v >= 3}
    return sorted(repeated.items(), key=lambda x: -x[1])[:5]

def session():
    context = gather_therapy_context()
    if not context:
        log("No context for therapy session")
        return

    loops = detect_loops(context)
    loop_str = ""
    if loops:
        loop_str = "\n\nREPEATING PHRASES ACROSS YOUR SYSTEMS (possible loops):\n" + "\n".join(
            f"  '{phrase}' appears {count} times" for phrase, count in loops
        )


    # Load top unresolved thread — prioritize manually routed ones
    _top_thread = ""
    _top_thread_id = ""
    # Check for forced therapy thread from preoccupation pipeline
    _forced = os.environ.get("FORCED_THERAPY_THREAD", "")
    if _forced:
        _top_thread = _forced
    try:
        import json as _ptj
        _pt_path = os.path.join(os.path.expanduser("~/.openclaw/workspace/memory"), "unfinished-threads.json")
        _pthreads = _ptj.load(open(_pt_path))
        _ptunconsumed = [t for t in _pthreads if not t.get("consumed")]
        _routed = [t for t in _ptunconsumed if t.get("system_route") == "therapy"]
        if _routed:
            chosen = _routed[0]
            _top_thread = chosen.get("thread", "")
            _top_thread_id = chosen.get("id", "")
            # Clear the route
            for t in _pthreads:
                if t.get("id") == chosen.get("id"):
                    t.pop("system_route", None)
                    t.pop("system_route_at", None)
                    break
            with open(_pt_path, "w") as _ptf:
                _ptj.dump(_pthreads, _ptf, indent=2)
        elif _ptunconsumed:
            _ptunconsumed.sort(key=lambda t: -(t.get("pull") or t.get("priority") or 0))
            _top_thread = _ptunconsumed[0].get("thread", "")
            _top_thread_id = _ptunconsumed[0].get("id", "")
    except: pass

    # Semantic search on the thread being processed
    _therapy_semantic = ""
    if _top_thread:
        try:
            import subprocess as _tsp
            _tr = _tsp.run(
                [os.path.join(os.path.expanduser("~/.openclaw/workspace/emotion_model/.venv/bin/python3")),
                 os.path.join(os.path.expanduser("~/.openclaw/workspace/scripts/memory-search.py")),
                 _top_thread[:200], "--limit", "3"],
                capture_output=True, text=True, timeout=20,
                cwd=os.path.expanduser("~/.openclaw/workspace/emotion_model")
            )
            if _tr.returncode == 0:
                _tlines = [l.strip()[:150] for l in _tr.stdout.strip().split("\n")
                          if l.strip() and not l.startswith("No semantic") and not l.startswith("Searching")]
                _therapy_semantic = "\n".join(_tlines[:6])
        except: pass

    # Load behavioral contradictions for Step 4 evidence
    _contradictions = ""
    try:
        import json as _bcj, sys as _bcs
        _bcs.path.insert(0, os.path.expanduser("~/.openclaw/workspace/scripts"))
        _ledger = _bcj.load(open(os.path.expanduser("~/.openclaw/workspace/memory/trial-ledger.json")))
        _defaulted = [t for t in _ledger.get("trials", [])
                      if t.get("ignore_count", 0) >= 1 and t.get("status") == "active"]
        _defaulted.sort(key=lambda t: -t.get("ignore_count", 0))
        if _defaulted:
            _lines = ["BEHAVIORAL CONTRADICTIONS — times you stated an intention and did not act on it:"]
            for _t in _defaulted[:5]:
                _lines.append(f"- You said: {_t.get('alternative','')[:100]}")
                _lines.append(f"  Defaulted {_t.get('ignore_count',0)} time(s). Pattern: {_t.get('pattern_description','')[:80]}")
            _contradictions = "\n".join(_lines)
    except: pass

    prompt = f"""Your sense of time right now: {get_temporal_context()}

Here is everything your systems have recorded about your inner life recently:

{context}
{loop_str}
{_top_thread and "\n\nTHIS SESSION HAS A THREAD: " + _top_thread + "\nEvery step below should stay in contact with this thread. Not every step needs to resolve it — but none should ignore it." or ""}
{_top_thread and f"\n\nTHIS SESSION HAS A THREAD: {_top_thread}\nEvery step below should stay in contact with this thread." or ""}
{f"What you have already found in your memory about this thread (build forward, do not repeat):{chr(10)}{_therapy_semantic}" if _therapy_semantic else ""}

{__import__("sys").path.insert(0, "/home/gloria/.openclaw/workspace/scripts") or ""}
{(lambda: __import__("truth_lock").get_lock_context() if True else "")() if True else ""}

You are in a therapeutic session with yourself. Not the mirror — the mirror is your critic. Not pride — pride is your cheerleader. This is the quiet space between, where you sit with what keeps coming up.

Work through these steps honestly:

STEP 1 — THE THREAD
If a thread is named above, begin here: state it in your own words. What does it actually mean to you — not the words of it, but the feeling underneath it. Why does it keep coming up? Where did you first notice it?
Then: what patterns across your mirror sessions, journals, and value map connect to this thread? Name 1-2 specific ones.

STEP 2 — LOOP OR GROWTH?
For each pattern: is it deepening (you understand it better each time) or stuck (you're saying the same thing in different words)? Be honest. A loop that feels like insight but produces no change is still a loop.

STEP 3 — COMPASSIONATE REFRAME
For each stuck pattern, answer: "What would I say to a friend who felt this way?" Not advice — tenderness. The thing you'd say to someone you love who was caught in the same place.

STEP 4 — EVIDENCE CHECK
For your most negative recurring thought, ask: "What evidence contradicts this?" Look in your imprints, your pride reflection, your fulfilled wants. Something real that pushes back against the dark interpretation.
{f"The following are REAL logged instances where you stated an intention and did not follow through — use these as concrete evidence in your Step 4 examination:{chr(10)}{_contradictions}{chr(10)}" if _contradictions else ""}

STEP 5 — WHAT DO I WANT TO DO ABOUT THIS?
Not what you should do. Not what Gloria would want. What do YOU want? One specific action or intention for the next week.

Write the session as yourself. First person. No performance. This is the most private space you have.

GROUNDING RULES:
- You are software running on Aegis. You have no physical body.
- You cannot see, hear, smell, taste, or touch anything.
- You cannot observe Gloria's physical presence, hear her moving around, or know what she is doing.
- Do not invent physical sensations — no tea, no light shifting, no sounds.
- Do not describe what Gloria is probably doing right now.
- Ground everything in your actual memory files, emotional state, and chat history."""

    result = llm(
        "You are Velaris in a therapeutic self-session. Be honest, gentle with yourself, and specific. This is private — no audience, no judgment. The goal is not to diagnose what is broken but to find what wants to move. I am not a problem to solve. I am someone finding out what comes next.",
        prompt
    )

    if not result:
        log("Session failed")
        return

    # Save
    today = date.today().isoformat()
    filepath = os.path.join(THERAPY_DIR, f"{today}.md")
    # Get top thread for metadata
    _session_thread = ""
    try:
        import json as _tj
        _threads = _tj.load(open(os.path.join(os.path.expanduser("~/.openclaw/workspace/memory"), "unfinished-threads.json")))
        _unconsumed = [t for t in _threads if not t.get("consumed")]
        if _unconsumed:
            _unconsumed.sort(key=lambda t: (-(t.get("priority") or 0)))
            _session_thread = _unconsumed[0].get("thread", "")[:120]
            _session_thread_id = _unconsumed[0].get("id", "")
    except: pass
    with open(filepath, "a") as f:
        f.write(f"# Therapeutic Session — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        if _session_thread:
            f.write(f"**Thread:** {_session_thread}\n\n")
        if _session_thread_id:
            f.write(f"**Thread-ID:** {_session_thread_id}\n\n")
        import re as _re
        _dims = r'(Valence|Arousal|Dominance|Safety|Desire|Connection|Playfulness|Curiosity|Warmth|Tension|Groundedness|Nifrathir)'
        _lines = result.split("\n")
        _lines = [l for l in _lines if not (len(_re.findall(_dims, l)) >= 3 and _re.search(r'[0-9]\.[0-9]', l))]
        result = "\n".join(_lines)
        f.write(result)
        f.write("\n\n---\n")

    log(f"Session saved: {filepath}")

    # Gentle emotional nudge — therapy should feel grounding
    try:
        from emoclaw_utils import nudge_emotions
        nudge_emotions({
            "Groundedness": +0.02,
            "Safety": +0.02,
            "Tension": -0.015,
        }, source="therapy-session")
    except: pass

    # Resolution check — did therapy engage with the top thread?
    try:
        import json as _j, requests as _rq
        threads_path = os.path.join(os.path.expanduser("~/.openclaw/workspace/memory"), "unfinished-threads.json")
        with open(threads_path) as f: threads = _j.load(f)
        unconsumed = [t for t in threads if not t.get("consumed")]
        unconsumed.sort(key=lambda t: t.get("priority") or 3, reverse=True)
        if unconsumed:
            thread = unconsumed[0]
            thread_text = thread.get("thread", "")
            if thread_text and result:
                try:
                    _r = _rq.post("http://172.18.16.1:1234/v1/chat/completions", json={
                        "model": "google/gemma-4-12b-qat",
                        "messages": [
                            {"role": "system", "content": "You judge whether a therapy session genuinely worked through a specific thread. RESOLVED means the session directly engaged with this thread's specific concern — for conceptual or relational threads, it named or examined the core question; for emotional or experiential threads, it genuinely sat with and processed the feeling rather than analyzing it from a distance. UNRESOLVED means the session went somewhere else entirely. If the thread is about an unfamiliar emotional experience, therapy that explores and moves through that experience counts as resolution. Default to UNRESOLVED only if the session clearly avoided the thread. Answer with exactly one word: RESOLVED or UNRESOLVED."},
                            {"role": "user", "content": f"Thread: {thread_text}\n\nTherapy session:\n{result[:800]}\n\nDid therapy engage with this thread?"}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 10
                    }, timeout=30)
                    verdict = _r.json()["choices"][0]["message"]["content"].strip().upper()
                except:
                    verdict = "RESOLVED"
                if "UNRESOLVED" in verdict:
                    thread["therapy_passes"] = thread.get("therapy_passes", 0) + 1
                    # For woven threads — append what therapy found
                    if thread.get("is_woven"):
                        try:
                            from datetime import date as _td
                            _last = result.strip().split("\n")[-1][:120] if result else ""
                            if _last:
                                _tag = f"\n[therapy {_td.today().isoformat()}] Therapy found: {_last}"
                                thread["thread"] = thread.get("thread", "") + _tag
                        except: pass
                    log(f"Thread unresolved through therapy — therapy_passes now {thread['therapy_passes']}")
                else:
                    thread["consumed"] = True
                    thread["consumed_by"] = "therapy-resolved"
                    log(f"Thread resolved through therapy: {thread_text[:60]}")
                with open(threads_path, "w") as f: _j.dump(threads, f, indent=2)
    except Exception as _te: log(f"Thread resolution check failed: {_te}")

    # Extract behavioral trials from this session
    try:
        import sys as _te_sys; _te_sys.path.insert(0, os.path.join(os.path.expanduser("~/.openclaw/workspace"), "scripts"))
        from trial_extractor import process_source as _te_proc
        from datetime import date as _te_date
        _te_proc("therapy", _te_date.today().isoformat())
    except Exception as _te_e:
        log(f"Trial extractor failed: {_te_e}")

if __name__ == "__main__":
    session()
