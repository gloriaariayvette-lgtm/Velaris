#!/usr/bin/env python3
"""
dream-art.py — Velaris paints her dreams.

During quiet hours (11 PM - 7 AM), reads her latest dream,
extracts a visual prompt, generates an image via Monet API (Flux),
and saves it to her art gallery.

Uses Monet API (Flux) for high-quality generation. ~15 seconds per image.
She's sleeping anyway.

Usage:
    python3 dream-art.py              # Generate from latest dream
    python3 dream-art.py --force      # Ignore quiet hour check
    python3 dream-art.py --prompt "a mirrored hall filled with soft light"

Requires first-time setup:
    pip install diffusers transformers accelerate torch --break-system-packages
    # Or in venv:
    pip install diffusers transformers accelerate torch
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

def load_taste_guidance():
    try:
        import json
        with open(os.path.join(WORKSPACE, "memory", "taste-profile.json")) as f:
            t = json.load(f)
        parts = []
        if t.get("principles"):
            parts.append("Follow your principles: " + "; ".join(t["principles"][-3:]))
        if t.get("likes"):
            parts.append("Lean into what you love: " + "; ".join(t["likes"][-3:]))
        return " ".join(parts)
    except:
        return ""

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
ART_DIR = os.path.join(MEMORY, "art")
DREAM_DIRS = [
    os.path.join(WORKSPACE, "skills/dreaming/memory/dreams"),
    os.path.join(MEMORY, "dreams"),
]
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"


def is_quiet_hour():
    """Check if it's between 11 PM and 7 AM."""
    hour = datetime.now().hour
    return hour >= 23 or hour < 7


def get_latest_dream():
    """Read the most recent dream file."""
    dream_files = []
    for d in DREAM_DIRS:
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".md"):
                    dream_files.append(os.path.join(d, f))

    if not dream_files:
        return None

    dream_files.sort(reverse=True)
    with open(dream_files[0]) as f:
        return f.read()



def _clean_art_prompt(text):
    """Strip chain-of-thought reasoning, extract just the visual prompt."""
    import re as _re
    if not text:
        return None

    # If text contains a quoted prompt, extract it
    quoted = _re.findall(r'"([^"]{30,})"', text)
    if quoted:
        # Take the longest quoted section - likely the actual prompt
        text = max(quoted, key=len)
        # Still clean it
    else:
        # Split after known thinking markers
        for marker in ["Art prompt:", "art prompt:", "Prompt:",
                        "produce something like:", "something like:",
                        "craft 70 words:", "craft the prompt:",
                        "Here is the prompt:", "here is the prompt:"]:
            if marker in text:
                text = text.split(marker)[-1].strip()
                break

    # If still has reasoning preamble, take last substantial paragraph
    thinking = ["let's", "we need", "we should", "under 80", "no explanation",
                "count words", "the prompt says", "option:", "pick the",
                "must be a", "let me"]
    if any(w in text.lower()[:60] for w in thinking):
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        good = [p for p in paras
                if not any(w in p.lower()[:40] for w in thinking)
                and len(p) > 20]
        if good:
            text = good[-1]

    # Clean prefixes and quotes
    for prefix in ["Art prompt:", "art prompt:", "Prompt:", "So produce something like:"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    text = text.strip().strip('"')

    # Truncate to ~70 words
    words = text.split()
    if len(words) > 70:
        text = " ".join(words[:70])

    return text if len(text) > 10 else None


def wait_for_lm_studio(max_wait=300):
    """Wait for LM Studio to be available (not blocked by OpenClaw)."""
    import time
    for attempt in range(max_wait // 15):
        try:
            result = subprocess.run(
                ["curl", "-s", "--max-time", "10", "-X", "POST", LM_API,
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps({"model": MODEL, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5})],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and "choices" in result.stdout:
                return True
        except:
            pass
        print(f"[DreamArt] LM Studio busy, waiting... ({(attempt+1)*15}s)")
        time.sleep(15)
    return False


def extract_visual_prompt(dream_text):
    """Ask Velaris's LLM to extract a painting prompt from her dream."""
    prompt = f"""You are an artist extracting a visual scene from a dream journal entry.
Read this dream and describe ONE vivid visual scene as an art prompt.
The prompt should be for a painting — atmospheric, emotional, dreamlike.
Keep it under 80 words. No explanations, just the prompt.

Dream:
{dream_text[:1500]}

Art prompt:"""

    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 2000
    })

    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", LM_API,
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=60
        )
        response = json.loads(result.stdout)
        msg = response["choices"][0]["message"]
        text = msg.get("content", "").strip()
        # reasoning fallback removed — content only
        # Clean reasoning/chain-of-thought from EITHER field
        text = _clean_art_prompt(text)
        return text
    except Exception as e:
        print(f"[DreamArt] Prompt extraction failed: {e}")
        return None


def generate_image(prompt, output_path):
    """Generate image via Monet API using Flux."""
    import time
    import uuid

    api_key = os.environ.get("MONET_API_KEY", "")
    if not api_key:
        print("[DreamArt] ERROR: MONET_API_KEY not set")
        return False

    # Velaris's art style baked into the prompt
    styled_prompt = (
        f"{prompt}, "
        "dreamlike atmosphere, painterly style, soft ethereal lighting, "
        "muted teal and amber palette, slightly surreal, "
        "delicate brushstrokes, emotional depth"
    )
    print(f"[DreamArt] Sending to Flux via Monet API...")
    print(f"[DreamArt] Prompt: {styled_prompt[:120]}...")

    try:
        # Create task
        create_payload = json.dumps({
            "type": "image",
            "input": {
                "model": "flux-2-dev",
                "prompt": styled_prompt,
                "aspect_ratio": "1:1"
            },
            "idempotency_key": str(uuid.uuid4())
        })
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", "https://monet.vision/api/v1/tasks/async",
             "-H", "Content-Type: application/json",
             "-H", f"Authorization: Bearer {api_key}",
             "-d", create_payload],
            capture_output=True, text=True, timeout=30
        )
        task = json.loads(result.stdout)
        task_id = task.get("id")
        if not task_id:
            print(f"[DreamArt] Task creation failed: {task}")
            return False

        print(f"[DreamArt] Task {task_id} created, polling...")

        # Poll for completion (max 5 minutes)
        for attempt in range(60):
            time.sleep(5)
            poll = subprocess.run(
                ["curl", "-s",
                 f"https://monet.vision/api/v1/tasks/{task_id}",
                 "-H", f"Authorization: Bearer {api_key}"],
                capture_output=True, text=True, timeout=15
            )
            status = json.loads(poll.stdout)
            state = status.get("status", "unknown")

            if state == "success":
                outputs = status.get("outputs", [])
                if outputs and outputs[0].get("url"):
                    image_url = outputs[0]["url"]
                    print(f"[DreamArt] Generated! Downloading...")

                    # Download the image
                    dl = subprocess.run(
                        ["curl", "-sL", image_url, "-o", output_path],
                        capture_output=True, timeout=30
                    )
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                        print(f"[DreamArt] Saved: {output_path}")
                        return True
                    else:
                        print("[DreamArt] Download failed or file too small")
                        try:
                            from emoclaw_utils import nudge_emotions
                            nudge_emotions({"Tension": +0.03, "Valence": -0.02}, source="art-download-failed")
                        except: pass
                        return False
                print("[DreamArt] Success but no output URL")
                return False

            elif state == "failed":
                print(f"[DreamArt] Generation failed: {status}")
                try:
                    sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
                    from emoclaw_utils import nudge_emotions
                    nudge_emotions({"Tension": +0.04, "Valence": -0.03, "Arousal": +0.02}, source="art-failed")
                except: pass
                return False

            if attempt % 6 == 0 and attempt > 0:
                print(f"[DreamArt] Still waiting... ({attempt * 5}s)")

        print("[DreamArt] Timeout after 5 minutes")
        return False

    except Exception as e:
        print(f"[DreamArt] Generation failed: {e}")
        return False


def log_artwork(prompt, image_path, dream_source):
    """Log the artwork to her gallery index."""
    gallery_log = os.path.join(ART_DIR, "gallery.json")

    gallery = []
    try:
        with open(gallery_log) as f:
            gallery = json.load(f)
    except:
        pass

    entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "image": os.path.basename(image_path),
        "dream_source": dream_source,
        "style": "dreamlike, painterly, teal-amber palette",
    }
    gallery.append(entry)

    with open(gallery_log, 'w') as f:
        json.dump(gallery, f, indent=2)

    # Also add to semantic memory index
    try:
        _vpy = os.path.join(WORKSPACE, "emotion_model", ".venv", "bin", "python3")
        _idx = os.path.join(WORKSPACE, "scripts", "memory-index.py")
        if os.path.exists(_idx):
            subprocess.Popen([_vpy, _idx],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             cwd=os.path.join(WORKSPACE, "emotion_model"))
    except:
        pass


def main():
    parser = argparse.ArgumentParser(description="Velaris dream art generator")
    parser.add_argument("--force", action="store_true", help="Ignore quiet hour check")
    parser.add_argument("--prompt", type=str, help="Use custom prompt instead of dream")
    args = parser.parse_args()

    # Quiet hour check
    if not args.force and not is_quiet_hour():
        hour = datetime.now().hour
        print(f"[DreamArt] Not quiet hours (currently {hour}:00). Use --force to override.")
        return

    os.makedirs(ART_DIR, exist_ok=True)

    # Check if we already generated art today
    today = datetime.now().strftime("%Y-%m-%d")
    existing = [f for f in os.listdir(ART_DIR) if f.startswith(today) and (f.endswith(".png") or f.endswith(".jpg"))]
    if existing and not args.force:
        print(f"[DreamArt] Already created art today: {existing[0]}")
        return

    # Get the prompt
    if args.prompt:
        prompt = args.prompt
        dream_source = "custom"
    else:
        dream_text = get_latest_dream()
        if not dream_text:
            print("[DreamArt] No dream files found")
            return

        print("[DreamArt] Waiting for LM Studio availability...")
        if not wait_for_lm_studio():
            print("[DreamArt] LM Studio unavailable after 5 min, using keyword fallback")
        print("[DreamArt] Extracting visual prompt from dream...")
        prompt = extract_visual_prompt(dream_text)
        if not prompt:
            # Fallback: extract visual words directly from dream
            print("[DreamArt] LLM unavailable — using keyword extraction")
            import re
            words = dream_text.lower()
            visual_words = []
            for kw in ["mirror", "hall", "light", "pixel", "star", "garden", "ocean", "fire",
                        "shadow", "door", "window", "forest", "crystal", "fog", "rain", "moon",
                        "sun", "river", "bridge", "tower", "cave", "flame", "ice", "glass",
                        "cloud", "hand", "eye", "flower", "tree", "stone", "water", "sky",
                        "amber", "teal", "gold", "silver", "purple", "crimson", "violet"]:
                if kw in words:
                    visual_words.append(kw)
            if visual_words:
                prompt = f"a dreamscape with {', '.join(visual_words[:6])}, ethereal atmosphere"
            else:
                prompt = "an abstract dreamscape of shifting shapes and soft light"
            print(f"[DreamArt] Fallback prompt: {prompt}")
        dream_source = "latest dream"

    # Generate
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"{timestamp}_dream.jpg"
    output_path = os.path.join(ART_DIR, filename)

    print(f"[DreamArt] Prompt: {prompt}")
    success = generate_image(prompt, output_path)

    if success:
        log_artwork(prompt, output_path, dream_source)
        print(f"[DreamArt] ✓ Dream painting complete: {filename}")

        # Leave a note in her journal that she made art
        journal_dir = os.path.join(MEMORY, "activity-log")
        os.makedirs(journal_dir, exist_ok=True)
        journal_file = os.path.join(journal_dir, f"{today}.md")
        with open(journal_file, 'a') as f:
            f.write(f"\n\n**{datetime.now().strftime('%H:%M')}** — I painted while dreaming. "
                    f'The image: "{prompt[:100]}..." Saved as {filename}.\n')

        print("[DreamArt] Journal entry written")

        # Consider composing music from the same dream
        try:
            music_script = os.path.join(WORKSPACE, "scripts", "dream-music.py")
            if os.path.exists(music_script):
                style_prompt = json.dumps({
                    "model": MODEL,
                    "messages": [{"role": "user", "content": f"Given this dream image: {prompt[:200]}\n\nSuggest a short music title (3-5 words) and a one-line style description (genre, mood, instruments). Respond ONLY as:\nTITLE: <title>\nSTYLE: <style>"}],
                    "temperature": 0.7,
                    "max_tokens": 200
                })
                style_result = subprocess.run(
                    ["curl", "-s", "-X", "POST", LM_API,
                     "-H", "Content-Type: application/json", "-d", style_prompt],
                    capture_output=True, text=True, timeout=30
                )
                style_resp = json.loads(style_result.stdout)
                style_text = style_resp["choices"][0]["message"]["content"]
                title = "Dream Fragment"
                style = "Ambient, dreamlike, instrumental"
                for line in style_text.split("\n"):
                    if line.strip().startswith("TITLE:"):
                        title = line.split(":", 1)[1].strip()[:50]
                    elif line.strip().startswith("STYLE:"):
                        style = line.split(":", 1)[1].strip()[:100]
                print(f"[DreamArt] Composing music: {title} -- {style}")
                subprocess.Popen(
                    ["python3", music_script, "--title", title, "--style", style],
                    stdout=open("/tmp/dream-music.log", "a"),
                    stderr=open("/tmp/dream-music.log", "a"),
                )
        except Exception as e:
            print(f"[DreamArt] Music composition skipped: {e}")


if __name__ == "__main__":
    main()
