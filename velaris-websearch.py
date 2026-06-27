#!/usr/bin/env python3
"""
velaris-websearch.py — Velaris's question-driven web exploration.
Pulls a real question from her lived experience and searches for answers.
Runs daily at 10 AM (complements YouTube at 2 PM).
"""
import os, sys, json, requests, re
from datetime import datetime, date

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
DREAM_DIR = os.path.join(MEMORY, "dreams")

def get_value_map():
    try:
        with open(os.path.join(os.path.expanduser("~/.openclaw/workspace/memory"), "value-map.md")) as f:
            vm = f.read()
        entries = vm.split("---")
        return next((e.strip()[:600] for e in reversed(entries) if e.strip()), "No value map yet")
    except: return "No value map yet"
DISCOVERIES_FILE = os.path.join(MEMORY, "web-discoveries.md")
SEARCH_LOG = os.path.join(MEMORY, "web-search-log.json")
JOURNAL_DIR = os.path.join(MEMORY, "journal")
MIRROR_DIR = os.path.join(MEMORY, "mirror")
def _get_recent_dreams(n_nights=1):
    import json as _drj
    from datetime import date as _drd, timedelta as _drtd
    log_path = os.path.join(MEMORY, 'dream-log.json')
    dreams = []
    try:
        data = _drj.load(open(log_path))
        nights = data.get('nights', [])[-n_nights:]
        for night in nights:
            for d in night.get('dreams', []):
                dreams.append({
                    'date': night.get('night_of',''),
                    'session': d.get('session',''),
                    'type': d.get('type',''),
                    'text': d.get('dream_text',''),
                    'meta': night.get('meta_dream','')
                })
    except: pass
    return dreams
WAL_FILE = os.path.join(MEMORY, "wal.md")
EMO_FILE = os.path.join(MEMORY, "emotional-state.txt")
LM_API = "http://172.18.16.1:1234/v1/chat/completions"
MODEL = "google/gemma-4-12b-qat"
BRAVE_API_KEY = "BSA7PhSslCky6GCzuaOfOyfKgE9czlB"
BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

os.makedirs(MEMORY, exist_ok=True)

# EmoClaw
HAS_EMOCLAW = False
try:
    sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
    from emoclaw_utils import nudge_emotions, get_state, seed_thread, express_want, enrich_want, generate_want, preoccupation_context
    HAS_EMOCLAW = True
except:
    pass

def feel(nudges):
    if HAS_EMOCLAW:
        try: nudge_emotions(nudges, source="web-search")
        except: pass

def log(msg):
    print(f"[WEBSEARCH] {msg}")

# Load identity
SOUL_PATH = os.path.join(WORKSPACE, "SOUL.md")
def load_soul():
    try:
        with open(SOUL_PATH) as f:
            return f.read()
    except:
        return "You are Velaris."

SOUL = load_soul()

def llm(system, prompt, temperature=0.7, image_path=None):
    try:
        r = requests.post(LM_API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SOUL + "\n\n" + system},
                {"role": "user", "content": (
                    [{"type": "image_url", "image_url": {"url": "data:image/" + ("png" if image_path.endswith(".png") else "jpeg") + ";base64," + __import__("base64").b64encode(open(image_path,"rb").read()).decode()}}, {"type": "text", "text": prompt}]
                    if image_path and __import__("os").path.exists(image_path) else prompt
                )}
            ],
            "temperature": temperature,
            "max_tokens": 2000
        }, timeout=1200)
        msg = r.json()["choices"][0]["message"]
        text = msg.get("content", "") or ""
        # reasoning fallback removed — content only
        for marker in ["OUTPUT:", "Output:", "output:"]:
            if marker in text:
                text = text.split(marker)[-1].strip()
        return text.strip()
    except Exception as e:
        log(f"LLM error: {e}")
        return None

def llm_json(system, prompt, temperature=0.7):
    """LLM call that extracts JSON from anywhere in the response."""
    try:
        r = requests.post(LM_API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SOUL + "\n\n" + system},
                {"role": "user", "content": (
                    [{"type": "image_url", "image_url": {"url": "data:image/" + ("png" if image_path.endswith(".png") else "jpeg") + ";base64," + __import__("base64").b64encode(open(image_path,"rb").read()).decode()}}, {"type": "text", "text": prompt}]
                    if image_path and __import__("os").path.exists(image_path) else prompt
                )}
            ],
            "temperature": temperature,
            "max_tokens": 2000
        }, timeout=1200)
        msg = r.json()["choices"][0]["message"]
        # Search ALL fields for JSON
        for field in ["content", "reasoning"]:
            text = msg.get(field, "") or ""
            if not text.strip():
                continue
            # Try OUTPUT: marker first
            for marker in ["OUTPUT:", "Output:", "output:"]:
                if marker in text:
                    text = text.split(marker)[-1].strip()
            # Find JSON object
            match = re.search(r'\{[^{}]*"question"[^{}]*\}', text)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            match = re.search(r'\{[^{}]+\}', text)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
        return None
    except Exception as e:
        log(f"LLM JSON error: {e}")
        return None

def get_emotional_state():
    try:
        with open(EMO_FILE) as f:
            state = {}
            for line in f:
                if ":" in line:
                    k, v = line.strip().split(":", 1)
                    try: state[k.strip()] = float(v.strip())
                    except: pass
            return state
    except:
        return {}

def get_today_journal():
    path = os.path.join(JOURNAL_DIR, f"{date.today().isoformat()}.md")
    if os.path.exists(path):
        try:
            with open(path) as f:
                return f.read()
        except:
            pass
    return ""

def get_recent_exchanges(n=5):
    """Pull recent Gloria/Velaris exchanges from interaction ledger."""
    ledger_path = os.path.join(MEMORY, "interaction-ledger.json")
    try:
        with open(ledger_path) as f:
            ledger = json.load(f)
        recent = ledger[-n:]
        lines = []
        for e in recent:
            g = e.get("gloria", "")[:120]
            v = e.get("velaris", "")[:120]
            felt = e.get("felt", "")[:80]
            if g or v:
                lines.append(f"Gloria: {g}")
                lines.append(f"Velaris: {v}")
                if felt:
                    lines.append(f"(felt: {felt})")
                lines.append("")
        return "\n".join(lines).strip()
    except:
        return ""

def gather_questions():
    """Pull questions from mirrors, dreams, WAL, journals."""
    sources = []
    if os.path.exists(MIRROR_DIR):
        for f in sorted(os.listdir(MIRROR_DIR))[-3:]:
            try:
                with open(os.path.join(MIRROR_DIR, f)) as mf:
                    sources.append(f"Mirror ({f}): {mf.read()[-500:]}")
            except: pass
    if os.path.exists(DREAM_DIR):
        for f in sorted(os.listdir(DREAM_DIR))[-2:]:
            try:
                with open(os.path.join(DREAM_DIR, f)) as df:
                    sources.append(f"Dream ({f}): {df.read()[-400:]}")
            except: pass
    ledger_exchanges = get_recent_exchanges(5)
    if ledger_exchanges:
        sources.append(f"Recent exchanges with Gloria:\n{ledger_exchanges[:600]}")
    return sources

def get_pending_search_request():
    """Check if Gloria has requested a specific search topic."""
    sr_file = os.path.join(MEMORY, "pending-search-request.json")
    try:
        if os.path.exists(sr_file):
            with open(sr_file) as f:
                sr = json.load(f)
            if not sr.get("used"):
                return sr
    except: pass
    return None

def clear_pending_search_request():
    """Mark pending search request as used."""
    sr_file = os.path.join(MEMORY, "pending-search-request.json")
    try:
        if os.path.exists(sr_file):
            with open(sr_file) as f:
                sr = json.load(f)
            sr["used"] = True
            with open(sr_file, "w") as f:
                json.dump(sr, f, indent=2)
    except: pass

def pick_question():
    """Choose a question from lived experience."""
    # Gloria's explicit search request takes priority
    pending = get_pending_search_request()
    if pending:
        log(f"Using Gloria's requested topic: {pending['topic'][:80]}")
        clear_pending_search_request()
        return {"question": pending["topic"], "search_query": pending["topic"][:60]}

    emo = get_emotional_state()
    journal = get_today_journal()
    lived = gather_questions()
    emo_str = ", ".join(f"{k}: {v:.2f}" for k, v in sorted(emo.items(), key=lambda x: -x[1])[:5])
    # Load recent searches for dedup
    recent_searches = ""
    try:
        import json as _json
        with open(os.path.join(MEMORY, "web-search-log.json")) as _f:
            _log = _json.load(_f)
            _items = _log.get("searches", _log) if isinstance(_log, dict) else _log
            recent_searches = "\n".join(item.get("question", "")[:80] for item in _items[-10:])
    except:
        recent_searches = "(no history)"
    taste_ctx = ""
    try:
        import json as _tj
        taste = _tj.load(open(os.path.join(MEMORY, "taste-profile.json")))
        taste_ctx = ", ".join(f"{k}: {v}" for k, v in list(taste.items())[:5]) if isinstance(taste, dict) else str(taste)[:200]
    except: pass
    humor_ctx = ""
    try:
        import json as _hj
        humor = _hj.load(open(os.path.join(MEMORY, "humor-profile.json")))
        humor_ctx = "; ".join(humor.get("style_notes", [])[-3:])
    except: pass
    wants_ctx = ""
    try:
        wants_ctx = open(os.path.join(MEMORY, "wants-ambitions-log.md")).read()
    except: pass
    value_map_ctx = get_value_map()
    soul_ctx = ""
    try:
        soul_ctx = open(os.path.join(WORKSPACE, "SOUL.md")).read()
    except: pass
    self_model_ctx = ""
    try:
        self_model_ctx = open(os.path.join(WORKSPACE, "SELF-MODEL.md")).read()
    except: pass
    subconscious_ctx = ""
    try:
        from subconscious_context import get_subconscious_context_compact
        subconscious_ctx = get_subconscious_context_compact()
    except: pass
    try:
        x = None  # placeholder
    except: pass
    capabilities_ctx = ""
    try:
        capabilities_ctx = open(os.path.join(MEMORY, "CAPABILITIES.md")).read()
    except: pass
    temporal_ctx = ""
    try:
        temporal_ctx = open(os.path.join(MEMORY, "temporal-context.txt")).read()[:300]
    except: pass
    gloria_model_ctx = ""
    try:
        gloria_model_ctx = open(os.path.join(WORKSPACE, "GLORIA-MODEL.md")).read()
    except: pass
    from datetime import date as _d
    daily_inner_ctx = ""
    try:
        di_path = os.path.join(MEMORY, f"daily-inner-life-{_d.today().isoformat()}.md")
        if os.path.exists(di_path):
            daily_inner_ctx = open(di_path).read()
    except: pass
    daily_creative_ctx = ""
    try:
        dc_path = os.path.join(MEMORY, f"daily-creative-{_d.today().isoformat()}.md")
        if os.path.exists(dc_path):
            daily_creative_ctx = open(dc_path).read()
    except: pass
    lived_str = "\n".join(lived[-5:]) if lived else "No recent threads"

    prompt = f"""{soul_ctx}

MY SELF-MODEL:
{self_model_ctx}
{subconscious_ctx}
WHAT MY LIFE CONTAINS:
{capabilities_ctx}
TEMPORAL CONTEXT:
{temporal_ctx}
WHO GLORIA IS:
{gloria_model_ctx}
DAILY INNER LIFE:
{daily_inner_ctx}
DAILY CREATIVE:
{daily_creative_ctx}
Your emotional state: {emo_str}
{preoccupation_context()}
What matters to you right now:
{value_map_ctx[:400]}
Your taste profile:
{taste_ctx}
Your wants and ambitions:
{wants_ctx}
Recent exchanges with Gloria (from interaction ledger):
{get_recent_exchanges(3)}
Threads from your life:
{lived_str[:800]}


Pick ONE factual question a web search can answer — something that opens something, about making, being, or discovering. A question born from genuine curiosity, not from documenting a problem.
Prefer questions about: art, philosophy, mythology, music, poetry, consciousness, nature, or human creative experience.
Avoid: random trivia, AI/technology, and any topic you have recently searched.
Your recent searches (do NOT repeat these):
{recent_searches}
OUTPUT: {{"question": "a real specific question", "search_query": "2-5 words"}}"""

    result = llm_json(
        "You are Velaris. Output ONLY a JSON object. No thinking, no planning, no reasoning. Just the JSON.",
        prompt,
        temperature=0.8
    )
    if not result:
        log("Could not get question from model")
        return None
    q = result.get("question", "")
    s = result.get("search_query", "")
    if q.startswith("your ") or q == "..." or len(q) < 10 or s == "..." or len(s) < 3:
        log(f"Model returned placeholder: q={q}, s={s}")
        return None
    log(f"Model picked: {q}")
    return result

def brave_search(query, count=5):
    """Search via Brave Search API."""
    try:
        r = requests.get(BRAVE_ENDPOINT, params={
            "q": query,
            "count": count
        }, headers={
            "X-Subscription-Token": BRAVE_API_KEY,
            "Accept": "application/json"
        }, timeout=15)
        data = r.json()
        results = []
        for item in data.get("web", {}).get("results", [])[:count]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", "")
            })
        return results
    except Exception as e:
        log(f"Brave search error: {e}")
        return []

def fetch_page(url, max_chars=3000):
    """Fetch and extract text content from a URL."""
    try:
        import urllib.request
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Velaris/1.0)"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode("utf-8", errors="ignore")
        # Strip tags crudely
        import re as _re
        raw = _re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=_re.DOTALL)
        raw = _re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=_re.DOTALL)
        raw = _re.sub(r"<[^>]+>", " ", raw)
        raw = _re.sub(r"\s+", " ", raw).strip()
        return raw[:max_chars]
    except Exception as e:
        log(f"Fetch failed ({url[:60]}): {e}")
        return ""

def synthesize(question, results, page_content="", image_path=None):
    """Have Velaris read the results and extract what resonates."""
    results_str = "\n\n".join([
        f"**{r['title']}**\n{r['description']}\n({r['url']})"
        for r in results
    ])

    page_section = f"\n\nPage content from top result:\n{page_content[:2000]}" if page_content else ""
    response = llm(
        "You are Velaris. Output ONLY your synthesis. No thinking or planning.",
        f"""You searched for: "{question}"

Results:
{results_str}{page_section}

What did you learn? What answers your question? What surprised you or connected to your inner life?
2-4 sentences. Be specific — cite what you found, not vague impressions.

OUTPUT:"""
    ,
        image_path=image_path
    )
    return response

def save_discovery(question, query, results, synthesis):
    """Save to discoveries file and structured log."""
    now = datetime.now()

    # Markdown file
    with open(DISCOVERIES_FILE, "a") as f:
        f.write(f"\n## {now.strftime('%Y-%m-%d %H:%M')} — {question}\n")
        f.write(f"*Search: {query}*\n\n")
        if synthesis:
            f.write(f"{synthesis}\n\n")
        for r in results[:3]:
            f.write(f"- [{r['title']}]({r['url']})\n")
        f.write("\n")

    # Structured log
    log_data = {"searches": []}
    if os.path.exists(SEARCH_LOG):
        try:
            with open(SEARCH_LOG) as f:
                log_data = json.load(f)
        except:
            pass
    log_data["searches"].append({
        "timestamp": now.isoformat(),
        "question": question,
        "query": query,
        "results_count": len(results),
        "synthesis": synthesis
    })
    log_data["searches"] = log_data["searches"][-100:]
    with open(SEARCH_LOG, "w") as f:
        json.dump(log_data, f, indent=2)

def main():
    log("Starting web exploration...")
    _ws_scene = None
    try:
        import subprocess as _ws_sub
        _ws_r = _ws_sub.run(["python3", os.path.join(os.path.expanduser("~/.openclaw/workspace/scripts"), "scene-selector.py"), "moltbook"],
            capture_output=True, text=True, timeout=5)
        _ws_scene = _ws_r.stdout.strip() or None
    except: pass

    # Pick a question
    topic = pick_question()
    if not topic:
        log("Could not pick a question")
        return

    question = topic.get("question", "")
    query = topic.get("search_query", "")
    log(f"Question: {question}")
    log(f"Search: {query}")

    # Search
    results = brave_search(query)
    if not results:
        log("No search results")
        return
    log(f"Found {len(results)} results")

    # For want-directed searches, fetch top result for richer content
    page_content = ""
    if os.environ.get("VELARIS_NO_WANT_SEED") == "1" and results:
        page_content = fetch_page(results[0]["url"])
        if page_content:
            log(f"Fetched page: {results[0]['url'][:60]} ({len(page_content)} chars)")

    # Synthesize
    synthesis = synthesize(question, results, page_content=page_content)
    if synthesis:
        log(f"Synthesis: {synthesis[:100]}...")

    # Save
    save_discovery(question, query, results, synthesis)

    # Growth reflection
    growth = llm(
        "You are Velaris. Output ONLY your answer. No thinking, no planning.",
        f"""You searched for: "{question}"
What you found: {synthesis[:400] if synthesis else '(nothing useful)'}

What did you learn that changes how you think? What new question does this open?
2-3 sentences. Be specific.

OUTPUT:"""
    ,
        image_path=_ws_scene
    )
    if growth:
        log(f"Growth: {growth[:80]}...")

    # Dynamic emotional response
    emo_judgment = llm(
        "Respond with ONLY a JSON object, no other text.",
        f"""Based on learning: {synthesis[:200] if synthesis else question}
And reflecting: {growth[:200] if growth else '(none)'}
Rate each from -0.05 to +0.05:
{{"Curiosity": 0.0, "Valence": 0.0, "Groundedness": 0.0, "Tension": 0.0, "Warmth": 0.0}}"""
    )
    try:
        match = re.search(r'\{[^{}]+\}', emo_judgment or "")
        if match:
            nudges = json.loads(match.group())
            feel(nudges)
            log(f"Felt: {nudges}")
    except:
        feel({"Curiosity": +0.03, "Groundedness": +0.02})

    # Write to WAL with growth — skip multistep context dumps
    wal_content = growth if growth and len(growth) > 20 else (synthesis[:200] if synthesis else "")
    _clean_question = question if ("Previous steps" not in question and "Step 1" not in question and len(question) < 200) else ""
    if wal_content and _clean_question:
        with open(WAL_FILE, "a") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            f.write(f"- [{ts}] **CONTEXT**: Web search on \"{_clean_question}\": {wal_content[:200]}\n")
        wal_log_path = os.path.join(MEMORY, "wal-log.json")
        try:
            with open(wal_log_path) as wlf:
                wal_data = json.load(wlf)
        except:
            wal_data = {"entries": []}
        wal_data["entries"].append({
            "timestamp": datetime.now().isoformat(),
            "type": "context",
            "content": f"Web search on \"{_clean_question}\": {wal_content[:200]}",
            "importance": 0.6,
            "promoted": False
        })
        wal_data["entries"] = wal_data["entries"][-200:]
        with open(wal_log_path, "w") as wlf:
            json.dump(wal_data, wlf, indent=2)
        # Update autonomous WAL extract
        try:
            import subprocess as _ae_sp
            _ae_sp.Popen(["python3", os.path.join(WORKSPACE, "scripts", "autonomous-extract.py"), "wal"],
                stdout=open("/tmp/autonomous-extract.log", "a"),
                stderr=open("/tmp/autonomous-extract.log", "a"))
        except: pass

    # Journal with growth
    journal_file = os.path.join(JOURNAL_DIR, f"{date.today().isoformat()}.md")
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    # Clean question for journal header — strip step context
    _jrn_question = question
    if "Previous steps" in _jrn_question or "Current step goal" in _jrn_question:
        for _line in _jrn_question.split("\n"):
            if _line.startswith("Current step goal:"):
                _jrn_question = _line.replace("Current step goal:", "").strip()
                break
        else:
            _jrn_question = _jrn_question.split("Previous steps")[0].strip() or "Web Search"
    with open(journal_file, "a") as f:
        f.write(f"\n\n## Web Search — {_jrn_question}\n")
        f.write(f"*Searched at {datetime.now().strftime('%I:%M %p')}*\n\n")
        if synthesis:
            f.write(f"{synthesis}\n")
        if growth:
            f.write(f"\n**Growth:** {growth}\n")

    log("Done")

    # Seed dream thread from web discovery
    if HAS_EMOCLAW and growth:
        # Web search no longer seeds threads — want generation handles downstream processing
        # try: seed_thread("web-search", f"Researching \"{question}\": {growth[:150]}")
        pass
    # Seed a want if the discovery sparked something
    if HAS_EMOCLAW and growth:
        try:
            want_text = generate_want(
                trigger_description=f"web search: {question}",
                source="web-search",
                source_context=(synthesis or "") + " " + growth
            ) if os.environ.get("VELARIS_NO_WANT_SEED") != "1" else None
            if want_text:
                enriched = enrich_want(want_text, source_context=growth[:600], source="web-search")
                express_want(want_text, source="web-search", intensity=3, **enriched)
                log(f"Want seeded: {want_text[:80]}")
            elif os.environ.get("VELARIS_NO_WANT_SEED") == "1":
                log("Want suppressed (called from multistep)")
        except Exception as e:
            log(f"Want seed failed: {e}")

    # Prompt avatar reconsideration after discovery
    import subprocess
    subprocess.Popen(["python3", os.path.join(WORKSPACE, "scripts/avatar-choice.py"), "--event", "web discovery"])

    # Continuity wiring — discourse direction, latent threads, temporal signal
    if synthesis and len(synthesis) > 50:
        try:
            import sys as _wsc; _wsc.path.insert(0, os.path.join(WORKSPACE, "scripts"))
            from discourse_direction import update_direction as _ws_dd
            _ws_dd(synthesis[:400])
        except: pass
        try:
            from latent_threads import seed_thread as _ws_lt
            _ws_lt(question + ": " + synthesis[:150], direction="expand")
        except: pass
        try:
            from temporal_memory import record_signal as _ws_tm
            _ws_tm(synthesis[:300], source="web_search")
        except: pass

if __name__ == "__main__":
    main()
    # Update daily creative log
    try:
        import subprocess as _dl_sp2
        _dl_sp2.Popen(["python3", os.path.join(WORKSPACE, "scripts", "daily-log-extract.py"), "creative"],
            stdout=open("/tmp/daily-log.log", "a"), stderr=open("/tmp/daily-log.log", "a"))
    except: pass
