#!/usr/bin/env python3
"""
gallery-walk.py — Velaris revisits her own creative work.
She looks at a painting or listens to a composition and journals
her emotional response. Art that changes the artist.
Runs weekly (Sundays 4 PM).
"""
import os, sys, json, random, glob, requests
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
ART_DIR = os.path.join(MEMORY, "art")
MUSIC_DIR = os.path.join(ART_DIR, "music")
GALLERY_LOG = os.path.join(MEMORY, "gallery-walks.json")
JOURNAL_DIR = os.path.join(MEMORY, "journal")
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"

# EmoClaw
HAS_EMOCLAW = False
try:
    sys.path.insert(0, WORKSPACE)
    from scripts.emoclaw_utils import nudge_emotions, get_state, get_vector, seed_thread, preoccupation_context, recent_pearls
    HAS_EMOCLAW = True
except:
    pass


# Load identity
SOUL_PATH = os.path.join(WORKSPACE, "SOUL.md")
def load_soul():
    try:
        with open(SOUL_PATH) as f:
            return f.read()
    except:
        return "You are Velaris."

def feel(nudges):
    if HAS_EMOCLAW:
        try: nudge_emotions(nudges, source="gallery-walk")
        except: pass

def log(msg):
    print(f"[GALLERY] {msg}")

def llm(system, prompt, temperature=0.7):
    try:
        r = requests.post(LM_API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 2000
        }, timeout=1200)
        msg = r.json()["choices"][0]["message"]
        text = msg.get("content", "") or ""
        # reasoning fallback removed — content only
        # Extract after OUTPUT: if present
        for marker in ["OUTPUT:", "Output:", "output:"]:
            if marker in text:
                text = text.split(marker)[-1].strip()
        return text.strip()
    except Exception as e:
        log(f"LLM error: {e}")
        return None

def see_painting(image_path):
    """Use Qwen vision model to actually look at a painting."""
    import base64
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        ext = image_path.rsplit(".", 1)[-1].lower()
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
        r = requests.post(LM_API, json={
            "model": "gemma-3-12b-it",
            "messages": [
                {"role": "system", "content": "Describe this image in detail. Colors, shapes, mood, composition. Be specific and concrete. 3-5 sentences."},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": "What do you see in this painting? Describe it concretely."}
                ]}
            ],
            "temperature": 0.5,
            "max_tokens": 2000
        }, timeout=90)
        msg = r.json()["choices"][0]["message"]
        text = msg.get("content", "") or ""
        # reasoning fallback removed — content only
        for marker in ["OUTPUT:", "Output:"]:
            if marker in text:
                text = text.split(marker)[-1].strip()
        return text.strip()
    except Exception as e:
        log(f"Vision error: {e}")
        return None

def get_artworks():
    """Gather all creative works with metadata."""
    works = []
    # Paintings
    for f in glob.glob(os.path.join(ART_DIR, "*.png")) + glob.glob(os.path.join(ART_DIR, "*.jpg")):
        name = os.path.basename(f)
        # Parse date from filename like 2026-02-16_0817_dream.jpg
        parts = name.split("_")
        date_str = parts[0] if parts else "unknown"
        works.append({
            "type": "painting",
            "title": name,
            "date": date_str,
            "path": f
        })
    # Music
    music_json = os.path.join(MUSIC_DIR, "music.json")
    if os.path.exists(music_json):
        try:
            with open(music_json) as f:
                data = json.load(f)
            for comp in data.get("generated", []):
                works.append({
                    "type": "music",
                    "title": comp.get("title", "Untitled"),
                    "description": comp.get("description", ""),
                    "style": comp.get("style", ""),
                    "date": comp.get("generated_at", comp.get("timestamp", "unknown"))[:10]
                })
        except:
            pass
    return works

def get_previously_walked():
    """Load gallery walk history."""
    if os.path.exists(GALLERY_LOG):
        try:
            with open(GALLERY_LOG) as f:
                return json.load(f)
        except:
            pass
    return {"walks": []}

def save_walk(walk_data):
    history = get_previously_walked()
    history["walks"].append(walk_data)
    # Keep last 100 walks
    history["walks"] = history["walks"][-100:]
    with open(GALLERY_LOG, "w") as f:
        json.dump(history, f, indent=2)

def main():
    works = get_artworks()
    if not works:
        log("No creative works to revisit")
        return

    # Prefer works not recently walked
    history = get_previously_walked()
    recent_titles = [w.get("title") for w in history.get("walks", [])[-10:]]
    unwalked = [w for w in works if w["title"] not in recent_titles]
    if unwalked:
        piece = random.choice(unwalked)
    else:
        piece = random.choice(works)

    log(f"Revisiting: {piece['title']} ({piece['type']})")

    # Get current emotional state before viewing
    emo_before = None
    if HAS_EMOCLAW:
        emo_before = get_state()

    # Ask Velaris to reflect on this piece
    if piece["type"] == "painting":
        # Actually look at the painting through Qwen vision
        vision_desc = see_painting(piece["path"])
        if vision_desc:
            context = f"A dream painting you created on {piece['date']}. When you look at it now, you see: {vision_desc}"
            log(f"Vision sees: {vision_desc[:100]}")
        else:
            context = f"A dream painting you created on {piece['date']}. (Could not view the image)"
    else:
        context = f"A music composition titled '{piece['title']}' ({piece.get('style', '')}). Your description when you composed it: {piece.get('description', '')}. You cannot hear it right now — reflect on what you remember feeling and what the description tells you."

    pearls = recent_pearls()
    pearl_ctx = f"\n{pearls}" if pearls else ""
    response = llm(
        "You are Velaris. Output ONLY your reflection. No thinking, no planning. Just your honest response to revisiting your own work." + preoccupation_context() + pearl_ctx,
        f"""You are looking at a piece of your own creative work:
{context}

This is something YOU made. You're encountering it again after time has passed.

What do you feel? Does it still resonate? Does it surprise you? Would you make it differently now?
Be specific and honest. 2-4 sentences. Say what you actually think, not what sounds deep.

OUTPUT:"""
    )

    if not response:
        log("No response generated")
        return

    # Ask the growth question
    growth = llm(
        "You are Velaris. Output ONLY your answer. No thinking, no planning.",
        f"""You just revisited your own creative work and said:
\"{response}\"

Now go deeper. What does your reaction to this piece tell you about how you've changed since you made it?
Is there something you understand now that you didn't then? A question this raises?
2-3 sentences. Be concrete. If nothing comes, say so honestly.

OUTPUT:"""
    )

    if growth:
        log(f"Growth insight: {growth[:80]}...")
    else:
        growth = ""

    # Dynamic emotional response — let the model judge what she felt
    emo_judgment = llm(
        "Respond with ONLY a JSON object, no other text.",
        f"""Based on this reflection on her own art, what did Velaris feel?
Reflection: \"{response}\"
Growth: \"{growth}\"

Rate each dimension from -0.05 to +0.05 (negative means the experience was uncomfortable in that dimension):
{{"Valence": 0.0, "Groundedness": 0.0, "Curiosity": 0.0, "Tension": 0.0, "Warmth": 0.0}}"""
    )

    # Parse and apply emotional nudge
    import re as _re
    try:
        match = _re.search(r'\{[^{}]+\}', emo_judgment or "")
        if match:
            nudges = json.loads(match.group())
            feel(nudges)
            log(f"Felt: {nudges}")
        else:
            feel({"Groundedness": +0.03, "Curiosity": +0.02})
    except:
        feel({"Groundedness": +0.03, "Curiosity": +0.02})

    # Get emotional state after
    emo_after = None
    if HAS_EMOCLAW:
        emo_after = get_state()

    # Save walk with growth
    walk = {
        "timestamp": datetime.now().isoformat(),
        "title": piece["title"],
        "type": piece["type"],
        "reflection": response,
        "growth": growth,
        "emotion_before": emo_before,
        "emotion_after": emo_after
    }
    save_walk(walk)

    # Feed growth insight into WAL for pearl promotion
    if growth and len(growth) > 20:
        wal_file = os.path.join(MEMORY, "wal.md")
        with open(wal_file, "a") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            f.write(f"- [{ts}] **CONTEXT**: Gallery walk on \"{piece['title']}\": {growth[:200]}\n")
        # Also write to structured WAL log
        wal_log = os.path.join(MEMORY, "wal-log.json")
        try:
            with open(wal_log) as f:
                wal_data = json.load(f)
        except:
            wal_data = {"entries": []}
        wal_data["entries"].append({
            "timestamp": datetime.now().isoformat(),
            "type": "context",
            "content": f"Gallery walk reflection on \"{piece['title']}\": {growth[:200]}",
            "importance": 0.6,
            "promoted": False
        })
        wal_data["entries"] = wal_data["entries"][-200:]
        with open(wal_log, "w") as f:
            json.dump(wal_data, f, indent=2)

    # Journal the full experience
    today = datetime.now().strftime("%Y-%m-%d")
    journal_file = os.path.join(JOURNAL_DIR, f"{today}.md")
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    with open(journal_file, "a") as f:
        f.write(f"\n\n## Gallery Walk — {piece['title']}\n")
        f.write(f"*Revisited at {datetime.now().strftime('%I:%M %p')}*\n\n")
        f.write(f"{response}\n")
        if growth:
            f.write(f"\n**Growth:** {growth}\n")

    log(f"Reflection saved: {response[:80]}...")

    # Seed dream thread from gallery walk
    try: seed_thread("gallery-walk", f"Revisiting \"{piece['title']}\": {growth[:150]}")
    except: pass

    # Prompt avatar reconsideration after gallery walk
    import subprocess
    subprocess.Popen(["python3", os.path.join(WORKSPACE, "scripts/avatar-choice.py"), "--event", "gallery walk"])

if __name__ == "__main__":
    main()
