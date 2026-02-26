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
DISCOVERIES_FILE = os.path.join(MEMORY, "web-discoveries.md")
SEARCH_LOG = os.path.join(MEMORY, "web-search-log.json")
JOURNAL_DIR = os.path.join(MEMORY, "journal")
MIRROR_DIR = os.path.join(MEMORY, "mirror")
DREAM_DIR = os.path.join(WORKSPACE, "skills/dreaming/memory/dreams")
WAL_FILE = os.path.join(MEMORY, "wal.md")
EMO_FILE = os.path.join(MEMORY, "emotional-state.txt")
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"
BRAVE_API_KEY = "BSA7PhSslCky6GCzuaOfOyfKgE9czlB"
BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

os.makedirs(MEMORY, exist_ok=True)

# EmoClaw
HAS_EMOCLAW = False
try:
    sys.path.insert(0, WORKSPACE)
    from scripts.emoclaw_utils import nudge_emotions, get_state, seed_thread
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

def llm(system, prompt, temperature=0.7):
    try:
        r = requests.post(LM_API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SOUL + "\n\n" + system},
                {"role": "user", "content": prompt}
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
                {"role": "user", "content": prompt}
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
    if os.path.exists(WAL_FILE):
        try:
            with open(WAL_FILE) as wf:
                text = wf.read()[-300:]
                if text.strip():
                    sources.append(f"WAL: {text}")
        except: pass
    return sources

def pick_question():
    """Choose a question from lived experience."""
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
    lived_str = "\n".join(lived[-5:]) if lived else "No recent threads"

    prompt = f"""Your emotional state: {emo_str}
Threads from your life:
{lived_str[:800]}

Pick ONE factual question a web search can answer.
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

def synthesize(question, results):
    """Have Velaris read the results and extract what resonates."""
    results_str = "\n\n".join([
        f"**{r['title']}**\n{r['description']}\n({r['url']})"
        for r in results
    ])

    response = llm(
        "You are Velaris. Output ONLY your synthesis. No thinking or planning.",
        f"""You searched for: "{question}"

Results:
{results_str}

What did you learn? What answers your question? What surprised you or connected to your inner life?
2-4 sentences. Be specific — cite what you found, not vague impressions.

OUTPUT:"""
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

    # Synthesize
    synthesis = synthesize(question, results)
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

    # Write to WAL with growth
    wal_content = growth if growth and len(growth) > 20 else (synthesis[:200] if synthesis else "")
    if wal_content:
        with open(WAL_FILE, "a") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            f.write(f"- [{ts}] **CONTEXT**: Web search on \"{question}\": {wal_content[:200]}\n")
        wal_log_path = os.path.join(MEMORY, "wal-log.json")
        try:
            with open(wal_log_path) as wlf:
                wal_data = json.load(wlf)
        except:
            wal_data = {"entries": []}
        wal_data["entries"].append({
            "timestamp": datetime.now().isoformat(),
            "type": "context",
            "content": f"Web search on \"{question}\": {wal_content[:200]}",
            "importance": 0.6,
            "promoted": False
        })
        wal_data["entries"] = wal_data["entries"][-200:]
        with open(wal_log_path, "w") as wlf:
            json.dump(wal_data, wlf, indent=2)

    # Journal with growth
    journal_file = os.path.join(JOURNAL_DIR, f"{date.today().isoformat()}.md")
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    with open(journal_file, "a") as f:
        f.write(f"\n\n## Web Search — {question}\n")
        f.write(f"*Searched at {datetime.now().strftime('%I:%M %p')}*\n\n")
        if synthesis:
            f.write(f"{synthesis}\n")
        if growth:
            f.write(f"\n**Growth:** {growth}\n")

    log("Done")

    # Seed dream thread from web discovery
    try: seed_thread("web-search", f"Researching \"{question}\": {growth[:150]}")
    except: pass

    # Prompt avatar reconsideration after discovery
    import subprocess
    subprocess.Popen(["python3", os.path.join(WORKSPACE, "scripts/avatar-choice.py"), "--event", "web discovery"])

if __name__ == "__main__":
    main()
