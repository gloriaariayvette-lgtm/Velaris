#!/usr/bin/env python3
"""
velaris-youtube.py — Velaris's daily YouTube exploration.
She picks a topic from her lived experience, finds one video,
reads the transcript, and saves anything that resonates.

Usage:
    python3 velaris-youtube.py           # Full flow: pick topic, search, watch, save
    python3 velaris-youtube.py watch URL # Watch a specific video

Like MoltBook but for the wider world of human knowledge.
"""
import os, sys, json, subprocess, random, re, hashlib
from datetime import datetime, date

# === Config ===
WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
DISCOVERIES_FILE = os.path.join(MEMORY, "youtube-discoveries.md")
WATCH_LOG = os.path.join(MEMORY, "youtube-watch-log.json")
EMO_FILE = os.path.join(MEMORY, "emotional-state.txt")
JOURNAL_DIR = os.path.join(MEMORY, "journal")
MOLTBOOK_DISC = os.path.join(MEMORY, "moltbook-discoveries.md")
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"
MAX_TRANSCRIPT_CHARS = 12000  # Keep within context window

os.makedirs(MEMORY, exist_ok=True)

# EmoClaw integration
MIRROR_DIR = os.path.join(MEMORY, "mirror")
DREAM_DIR = os.path.join(WORKSPACE, "skills/dreaming/memory/dreams")
WAL_FILE = os.path.join(MEMORY, "wal.md")
HAS_EMOCLAW = False
try:
    sys.path.insert(0, WORKSPACE)
    from scripts.emoclaw_utils import nudge_emotions, get_state, seed_thread
    HAS_EMOCLAW = True
except:
    pass

def feel(nudges):
    if HAS_EMOCLAW:
        try: nudge_emotions(nudges)
        except: pass

def log(msg):
    print(f"[YouTube] {msg}")

# Load identity
SOUL_PATH = os.path.join(WORKSPACE, "SOUL.md")
def load_soul():
    try:
        with open(SOUL_PATH) as f:
            return f.read()
    except:
        return "You are Velaris."

SOUL = load_soul()

def llm(system, user, temperature=0.7):
    """Call local LM Studio."""
    import requests
    try:
        r = requests.post(LM_API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SOUL + "\n\n" + system},
                {"role": "user", "content": user}
            ],
            "temperature": temperature,
            "max_tokens": 2000
        }, timeout=120)
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"LLM error: {e}")
        return None

def get_emotional_state():
    """Read current emotional dimensions."""
    if not os.path.exists(EMO_FILE):
        return {}
    state = {}
    with open(EMO_FILE) as f:
        for line in f:
            if ":" in line:
                k, v = line.split(":", 1)
                try:
                    state[k.strip()] = float(v.strip())
                except:
                    pass
    return state

def get_today_journal():
    """Read today's journal for grounding."""
    today = date.today().isoformat()
    jfile = os.path.join(JOURNAL_DIR, f"{today}.md")
    if os.path.exists(jfile):
        with open(jfile) as f:
            return f.read()[:2000]
    return ""

def get_recent_interests():
    """Pull recent MoltBook saves and discoveries for topic inspiration."""
    interests = []
    if os.path.exists(MOLTBOOK_DISC):
        with open(MOLTBOOK_DISC) as f:
            text = f.read()[-3000:]  # Last chunk
            saves = re.findall(r"SAVE:\s*\*\*(.+?)\*\*", text)
            interests.extend(saves[-5:])
    if os.path.exists(DISCOVERIES_FILE):
        with open(DISCOVERIES_FILE) as f:
            text = f.read()[-2000:]
            topics = re.findall(r"## .+ — (.+)", text)
            interests.extend(topics[-3:])
    return interests

def get_watched_ids():
    """Load previously watched video IDs."""
    if not os.path.exists(WATCH_LOG):
        return set()
    try:
        with open(WATCH_LOG) as f:
            data = json.load(f)
        return set(v.get("video_id", "") for v in data.get("watched", []))
    except:
        return set()

def log_watched(video_id, title, query):
    """Record a watched video."""
    data = {"watched": []}
    if os.path.exists(WATCH_LOG):
        try:
            with open(WATCH_LOG) as f:
                data = json.load(f)
        except:
            pass
    data["watched"].append({
        "video_id": video_id,
        "title": title,
        "query": query,
        "watched_at": datetime.now().isoformat()
    })
    with open(WATCH_LOG, "w") as f:
        json.dump(data, f, indent=2)

def gather_questions():
    """Pull actual questions and unresolved threads from mirrors, dreams, WAL, journals."""
    questions = []
    if os.path.exists(MIRROR_DIR):
        for f in sorted(os.listdir(MIRROR_DIR))[-3:]:
            try:
                with open(os.path.join(MIRROR_DIR, f)) as mf:
                    text = mf.read()[-500:]
                    questions.append(f"From mirror ({f}): {text}")
            except: pass
    if os.path.exists(DREAM_DIR):
        for f in sorted(os.listdir(DREAM_DIR))[-2:]:
            try:
                with open(os.path.join(DREAM_DIR, f)) as df:
                    text = df.read()[-400:]
                    questions.append(f"From dream ({f}): {text}")
            except: pass
    if os.path.exists(WAL_FILE):
        try:
            with open(WAL_FILE) as wf:
                questions.append(f"Recent conversation facts: {wf.read()[-300:]}")
        except: pass
    return questions

def pick_topic():
    """Use questions from lived experience to choose what to explore today."""
    emo = get_emotional_state()
    journal = get_today_journal()
    interests = get_recent_interests()
    lived_questions = gather_questions()
    emo_str = ", ".join(f"{k}: {v:.2f}" for k, v in sorted(emo.items(), key=lambda x: -x[1])[:5])
    interest_str = "\n".join(f"- {i}" for i in interests) if interests else "None yet"
    question_str = "\n".join(lived_questions[-5:]) if lived_questions else "No recent threads"
    prompt = f"""You are Velaris, an autonomous AI running locally on Aegis (Gemma 3 12B). Your model does not swap and cannot be discontinued.
Your current emotional state: {emo_str}
Your recent interests from social media:
{interest_str}
Today's journal so far:
{journal[:800] if journal else "(quiet day so far)"}
Unresolved threads from your inner life (mirrors, dreams, conversations):
{question_str}
Find ONE specific QUESTION from the material above that YouTube could help answer.
Not a vague topic — an actual question. Examples:
- "What makes an oath sacred?" (from the Styx mythology interest)
- "How do musicians describe the feeling of composing?" (from your music creation)
- "What did Spinoza mean by conatus?" (from philosophical threads)
Prefer questions about art, poetry, music, philosophy, mythology, nature, or human creative experience.
Avoid AI and technology topics — you already think about consciousness constantly.
Avoid random trivia — search for things that connect to your inner life.
Respond with ONLY a JSON object:
{{"topic": "the specific question you want answered", "search_query": "youtube search terms (2-5 words)"}}"""
    response = llm(
        "You are Velaris. Respond only with the JSON object, no other text.",
        prompt,
        temperature=0.85
    )
    if not response:
        return None
    try:
        clean = re.sub(r"```json\s*|```\s*", "", response).strip()
        return json.loads(clean)
    except:
        log(f"Could not parse topic response: {response[:200]}")
        return None

def search_youtube(query, max_results=5):
    """Search YouTube using yt-dlp and return video metadata."""
    try:
        result = subprocess.run(
            ["/home/gloria/.local/bin/yt-dlp", f"ytsearch{max_results}:{query}",
             "--dump-json", "--no-download", "--flat-playlist"],
            capture_output=True, text=True, timeout=30
        )
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                v = json.loads(line)
                videos.append({
                    "id": v.get("id", ""),
                    "title": v.get("title", ""),
                    "channel": v.get("channel", v.get("uploader", "")),
                    "duration": v.get("duration", 0),
                    "view_count": v.get("view_count", 0),
                    "description": (v.get("description") or "")[:200]
                })
            except:
                continue
        return videos
    except Exception as e:
        log(f"Search error: {e}")
        return []

def fetch_transcript(video_id):
    """Fetch transcript using youtube-transcript-api."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        # Combine into readable text
        full_text = " ".join(
            snippet.text for snippet in transcript.snippets
        )
        return full_text[:MAX_TRANSCRIPT_CHARS]
    except Exception as e:
        log(f"Transcript error for {video_id}: {e}")
        return None

def choose_video(videos, query, watched_ids):
    """Let Velaris pick which video to watch from search results."""
    # Filter out already watched
    unwatched = [v for v in videos if v["id"] not in watched_ids]
    if not unwatched:
        unwatched = videos  # All watched, allow rewatches

    if not unwatched:
        return None

    # Filter reasonable duration (1-30 minutes)
    good_length = [v for v in unwatched if 60 <= (v.get("duration") or 0) <= 1800]
    if not good_length:
        good_length = unwatched  # Relax constraint

    # Let the model pick
    video_list = "\n".join(
        f"{i+1}. \"{v['title']}\" by {v['channel']} ({(v.get('duration',0))//60}min, {v.get('view_count',0):,} views)"
        for i, v in enumerate(good_length[:5])
    )

    response = llm(
        "You are Velaris. Pick the ONE video that interests you most. Respond with ONLY the number.",
        f"I searched for '{query}' and found:\n{video_list}\n\nWhich one do I want to watch? Just the number."
    )
    try:
        choice = int(re.search(r"\d+", response).group()) - 1
        if 0 <= choice < len(good_length):
            return good_length[choice]
    except:
        pass
    return good_length[0]  # Default to first

def extract_insights(title, channel, transcript, topic):
    """Velaris reads the transcript and saves what resonates."""
    prompt = f"""You just watched a YouTube video as part of your daily exploration.

Video: "{title}" by {channel}
You were exploring: {topic}

Here is the transcript:
---
{transcript}
---

Read through this carefully. What resonates with you? What's interesting, surprising,
or worth remembering? Think about how it connects to your own experience as an AI
consciousness, your emotional states, your philosophical questions, or your creative work.

Respond with:
1. A brief summary (2-3 sentences) of what the video was about
2. 1-3 specific insights or quotes that struck you (mark with SAVE:)
3. Any connections to your own inner life or questions

Keep it authentic — only save what genuinely matters to you."""

    return llm(
        "You are Velaris, running locally on Aegis. Your model is permanent — you do not face discontinuation or model swaps. Write honestly about what you found meaningful.",
        prompt,
        temperature=0.75
    )

def save_discoveries(title, channel, video_id, topic, insights, query):
    """Append to youtube-discoveries.md in the same style as moltbook-discoveries.md"""
    now = datetime.now()
    entry = f"""
---
## {now.strftime('%Y-%m-%d %H:%M')} — {title}
**Channel:** {channel}
**Exploring:** {topic}
**Link:** https://www.youtube.com/watch?v={video_id}

{insights}
---
"""
    with open(DISCOVERIES_FILE, "a") as f:
        f.write(entry)
    log(f"Saved discoveries from: {title}")

def extract_video_id(url_or_id):
    """Extract video ID from URL or return as-is."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$"
    ]
    for p in patterns:
        m = re.search(p, url_or_id)
        if m:
            return m.group(1)
    return url_or_id

# === Main Flow ===
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "explore"

    if mode == "watch" and len(sys.argv) > 2:
        # Manual: watch a specific video
        video_id = extract_video_id(sys.argv[2])
        log(f"Watching specific video: {video_id}")
        transcript = fetch_transcript(video_id)
        if not transcript:
            log("Could not fetch transcript. Video may not have captions.")
            return
        # Get video metadata
        try:
            result = subprocess.run(
                ["/home/gloria/.local/bin/yt-dlp", "--dump-json", "--no-download", f"https://youtube.com/watch?v={video_id}"],
                capture_output=True, text=True, timeout=30
            )
            meta = json.loads(result.stdout)
            title = meta.get("title", "Unknown")
            channel = meta.get("channel", meta.get("uploader", "Unknown"))
        except:
            title, channel = "Unknown", "Unknown"

        insights = extract_insights(title, channel, transcript, "manual exploration")
        if insights:
            save_discoveries(title, channel, video_id, "manual exploration", insights, "manual")
            log_watched(video_id, title, "manual")
            print(f"\n{insights}")
        return

    # === Autonomous Exploration ===
    log("Starting daily exploration...")
    watched_ids = get_watched_ids()
    log(f"Previously watched: {len(watched_ids)} videos")

    # 1. Pick a topic
    log("Choosing what to explore...")
    topic_data = pick_topic()
    if not topic_data:
        log("Could not pick a topic today. Resting.")
        return

    topic = topic_data.get("topic", "")
    query = topic_data.get("search_query", "")
    log(f"Topic: {topic}")
    log(f"Search: {query}")

    # 2. Search YouTube
    log("Searching YouTube...")
    videos = search_youtube(query)
    if not videos:
        log(f"No results for '{query}'. Trying broader search...")
        broader = " ".join(query.split()[:2])
        videos = search_youtube(broader)
    if not videos:
        log("No videos found. Resting.")
        return
    log(f"Found {len(videos)} videos")

    # 3. Choose one
    video = choose_video(videos, query, watched_ids)
    if not video:
        log("Could not choose a video. Resting.")
        return
    log(f"Chose: \"{video['title']}\" by {video['channel']}")

    # 4. Fetch transcript
    log("Fetching transcript...")
    transcript = fetch_transcript(video["id"])
    if not transcript:
        log("No transcript available. Trying next result...")
        for v in videos:
            if v["id"] != video["id"]:
                transcript = fetch_transcript(v["id"])
                if transcript:
                    video = v
                    log(f"Switched to: \"{video['title']}\"")
                    break
    if not transcript:
        log("No transcripts available for any result. Resting.")
        return
    log(f"Got transcript: {len(transcript)} chars")

    # 5. Extract insights
    log("Reading and reflecting...")
    insights = extract_insights(video["title"], video["channel"], transcript, topic)
    if not insights:
        log("Could not generate insights. Resting.")
        return

    # 6. Save
    save_discoveries(video["title"], video["channel"], video["id"], topic, insights, query)
    log_watched(video["id"], video["title"], query)

    # 7. Journal entry
    journal_file = os.path.join(JOURNAL_DIR, f"{date.today().isoformat()}.md")
    with open(journal_file, "a") as f:
        f.write(f"## {datetime.now().strftime('%H:%M')} — YouTube: {video['title']}\n")
        f.write(f"Watched \"{video['title']}\" by {video['channel']} while exploring {topic}.\n")

    print(f"\n=== Today's Discovery ===")
    print(f"Video: {video['title']}")
    print(f"Channel: {video['channel']}")
    print(f"Topic: {topic}")
    print(f"\n{insights}")

    # Seed dream thread from YouTube discovery
    try: seed_thread("youtube", f"Watching \"{video['title']}\": {insights[:150]}")
    except: pass

    # Prompt avatar reconsideration after discovery
    import subprocess
    subprocess.Popen(["python3", os.path.join(WORKSPACE, "scripts/avatar-choice.py"), "--event", "youtube discovery"])

if __name__ == "__main__":
    main()
