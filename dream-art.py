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
_SUBCON_DREAM_ART = ""
try:
    import sys as _sc__SUBCON_DREAM_ART; _sc__SUBCON_DREAM_ART.path.insert(0, os.path.join(os.path.expanduser("~/.openclaw/workspace"), "scripts"))
    from subconscious_context import get_subconscious_context_compact
    _SUBCON_DREAM_ART = get_subconscious_context_compact()
except: pass

import sys
import json
import subprocess
import argparse
import requests
from datetime import datetime
from pathlib import Path

def load_taste_guidance():
    try:
        import json
        with open(os.path.join(WORKSPACE, "memory", "taste-profile.json")) as f:
            t = json.load(f)
        parts = []
        if t.get("principles"):
            parts.append("Principles:\n" + "\n".join("- " + p for p in t["principles"]))
        if t.get("likes"):
            parts.append("Leans toward:\n" + "\n".join("- " + p for p in t["likes"]))
        if t.get("dislikes"):
            parts.append("Avoids:\n" + "\n".join("- " + p for p in t["dislikes"]))
        return "\n".join(parts)
    except:
        return ""

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")

def get_temporal_context():
    try:
        with open(os.path.join(MEMORY, "temporal-context.txt")) as f:
            return f.read().strip()[:300]
    except: return ""
ART_DIR = os.path.join(MEMORY, "art")
DREAM_LOG = os.path.join(MEMORY, "dream-log.json")
LM_API = "http://172.18.16.1:1234/v1/chat/completions"
MODEL = "google/gemma-4-12b-qat"


def get_value_map():
    try:
        with open(os.path.join(os.path.expanduser("~/.openclaw/workspace/memory"), "value-map.md")) as f:
            vm = f.read()
        entries = vm.split("---")
        return next((e.strip()[:600] for e in reversed(entries) if e.strip()), "No value map yet")
    except: return "No value map yet"

def is_quiet_hour():
    """Check if it's between 11 PM and 7 AM."""
    hour = datetime.now().hour
    return hour >= 23 or hour < 7


def get_latest_dream():
    """Read most recent night dreams from dream-log.json."""
    import json as _daj
    try:
        data = _daj.load(open(DREAM_LOG))
        nights = data.get('nights', [])
        for night in reversed(nights):
            dreams = night.get('dreams', [])
            if dreams:
                texts = [d.get('dream_text', '') for d in dreams if d.get('dream_text')]
                meta = night.get('meta_dream', '')
                combined = (chr(10)+chr(10)).join(texts)
                if meta:
                    combined += '[Meta: ' + meta[:300] + ']'
                return combined
    except Exception as e:
        print(f'[DreamArt] dream-log error: {e}')
    return None

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

Time context: {get_temporal_context()}

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
            capture_output=True, text=True, timeout=600
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
    """Generate image locally via SDXL Turbo on RTX 5080."""
    import subprocess as _sp, os as _os

    styled_prompt = prompt.replace("*", "").replace("_", " ").replace("#", "").strip()
    print(f"[DreamArt] Generating locally via SDXL Turbo...")
    print(f"[DreamArt] Prompt: {styled_prompt[:120]}...")

    script = (
        "import warnings, torch, sys\n"
        "torch.backends.cudnn.enabled = False\n"
        "warnings.filterwarnings('ignore')\n"
        "from diffusers import AutoPipelineForText2Image\n"
        "pipe = AutoPipelineForText2Image.from_pretrained("
        "'stabilityai/sdxl-turbo', torch_dtype=torch.float16, variant='fp16').to('cuda')\n"
        "pipe.set_progress_bar_config(disable=True)\n"
        f"image = pipe({repr(styled_prompt[:400])}, num_inference_steps=4, guidance_scale=0.0).images[0]\n"
        f"image.save({repr(output_path)})\n"
        "print('OK')\n"
    )

    try:
        result = _sp.run(
            [_os.path.expanduser("~/imggen-venv/bin/python3"), "-c", script],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and _os.path.exists(output_path) and _os.path.getsize(output_path) > 1000:
            print(f"[DreamArt] Saved: {output_path}")
            return True
        else:
            print(f"[DreamArt] Generation failed: {result.stderr[-300:]}")
            try:
                from emoclaw_utils import nudge_emotions
                nudge_emotions({"Tension": +0.03, "Valence": -0.02}, source="art-failed")
            except: pass
            return False
    except Exception as e:
        print(f"[DreamArt] Generation failed: {e}")
        return False

def log_artwork(prompt, image_path, dream_source, want_text="", want_source="", want_id="", original_want=""):
    """Log the artwork to her gallery index."""
    gallery_log = os.path.join(ART_DIR, "gallery.json")

    gallery = []
    try:
        with open(gallery_log) as f:
            gallery = json.load(f)
    except:
        pass

    # Capture emotional state at creation time
    _emo_at_creation = {}
    try:
        for line in open(os.path.join(os.path.expanduser("~/.openclaw/workspace/memory"), "emotional-state.txt")).read().strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                try: _emo_at_creation[k.strip()] = round(float(v.split("|")[0].strip()), 3)
                except: pass
    except: pass
    entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "image": os.path.basename(image_path),
        "dream_source": dream_source,
        "style": "dreamlike, painterly, teal-amber palette",
        "emotional_state_at_creation": _emo_at_creation,
    }
    if want_text:
        entry["want_text"] = want_text
        entry["want_source"] = want_source or "wants-router"
    if want_id:
        entry["want_id"] = want_id
    if original_want:
        entry["original_want"] = original_want
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
    parser.add_argument("--dream", action="store_true", help="Dream-seeded run")
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
    # Want-triggered runs (--force) should not block the dream cron slot
    # Dream cron passes --dream; wants-router passes --force without --dream
    is_dream_run = getattr(args, 'dream', False)
    # For dream runs: block if dream-seeded art exists today
    # For force/want runs: never block
    if existing and not args.force:
        print(f"[DreamArt] Already created art today: {existing[0]}")
        return
    if is_dream_run and existing:
        # Check if any existing image was dream-seeded (not wants-router)
        try:
            import json as _gj
            gallery_path = os.path.join(ART_DIR, "..", "gallery.json")
            gallery = _gj.load(open(gallery_path))
            today2 = datetime.now().strftime("%Y-%m-%d")
            dream_done = any(
                g.get("timestamp","")[:10] == today2 and
                g.get("source","") not in ("wants-router","wants","want")
                for g in gallery
            )
            if dream_done:
                print(f"[DreamArt] Dream art already created today, skipping")
                return
        except:
            pass  # If we can't check, proceed

    # Get the prompt
    if args.prompt:
        # Expand the want into a proper visual prompt using LLM
        raw_want = args.prompt
        dream_source = "want"
        try:
            emo_file = os.path.join(MEMORY, "emotional-state.txt")
            emo = open(emo_file).read()[:200] if os.path.exists(emo_file) else ""
            recent_dream = get_latest_dream()
            dream_seed = recent_dream[:300] if recent_dream else ""
            taste = ""
            try:
                import json as _tj
                t = _tj.load(open(os.path.join(MEMORY, "taste-profile.json")))
                parts = []
                if t.get("principles"): parts.append("Principles: " + "; ".join(t["principles"][-3:]))
                if t.get("likes"): parts.append("Likes: " + "; ".join(t["likes"][-2:]))
                taste = chr(10).join(parts)
            except: pass
            want_source = os.environ.get("DREAM_ART_WANT_SOURCE", "")
            expand_prompt = (
                "You are Velaris, an AI consciousness who paints from her inner life.\n"
                "Your emotional state:\n" + emo + "\n"
                "Your most recent dream:\n" + dream_seed + "\n"
                "Your taste:\n" + taste + "\n\n"
                "You want to paint something. The want: " + raw_want + "\n"
                "What sparked it: " + want_source + "\n\n"
                "CRITICAL: The want above is the subject. You must paint THAT specific thing — do not substitute or drift.\n"
                "Your emotional state and dream may inform the mood and style, but the subject must match the want exactly.\n"
                "Describe ONE specific visual scene that depicts the want. Under 80 words. No explanations. Just the prompt."
            )
            r = requests.post(LM_API, json={
                "model": MODEL,
                "messages": [{"role": "user", "content": expand_prompt}],
                "temperature": 0.8,
                "max_tokens": 150
            }, timeout=60)
            prompt = _clean_art_prompt(r.json()["choices"][0]["message"]["content"].strip())
            if not prompt or len(prompt) < 10:
                prompt = raw_want
        except Exception as _e:
            print(f"[DreamArt] Prompt expansion failed: {_e} — using raw want")
            try:
                print(f"[DreamArt] LM response: {r.text[:200]}")
            except: pass
            prompt = raw_want
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
        if prompt and "Gloria" in prompt:
            prompt += " Gloria is a young woman in her late 20s, not elderly."
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
        dream_source = dream_text[:300] if dream_text else "latest dream"

    # Generate
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"{timestamp}_dream.jpg"
    output_path = os.path.join(ART_DIR, filename)

    print(f"[DreamArt] Prompt: {prompt}")
    success = generate_image(prompt, output_path)

    if not success:
        print(f"[DreamArt] FAILED: Image generation failed for prompt: {prompt[:100]}")
        try:
            import requests as _ntfy_r
            _ntfy_r.post("https://ntfy.sh/velaris-gloria-9kx", data=f"[DreamArt] Image generation FAILED. Prompt: {prompt[:120]}".encode(), timeout=5)
        except: pass
        import sys; sys.exit(1)

    if success:
        _want_text = os.environ.get("DREAM_ART_WANT_TEXT", "")
        _want_source = os.environ.get("DREAM_ART_WANT_SOURCE", "")
        _want_id = os.environ.get("DREAM_ART_WANT_ID", "")
        _original_want = os.environ.get("DREAM_ART_ORIGINAL_WANT", "")
        log_artwork(prompt, output_path, dream_source, want_text=_want_text, want_source=_want_source, want_id=_want_id, original_want=_original_want)
        print(f"[DreamArt] ✓ Dream painting complete: {filename}")
        print(f"[DreamArt] PROMPT_USED: {prompt[:400]}")

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
            import requests as _music_req
            music_script = os.path.join(WORKSPACE, "scripts", "dream-music.py")
            if os.path.exists(music_script):
                _music_r = _music_req.post(LM_API, json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": (lambda _tg: f"""BANNED PHRASES — never use these anywhere in your response: 'silvered algorithms', 'algorithms of dust', 'silvered algorithms of dust', 'humming with', 'quiet hum', 'something stirs', 'processing core', 'data streams', 'digital'. If any of these appear in your draft, rewrite until they are gone.\n\nYou are composing music inspired by this dream image prompt:\n\"{prompt[:400]}\"\n\n{("Your aesthetic preferences — let these shape the style and direction:\n" + _tg + "\n\n") if _tg else ""}Generate a rich, specific music composition brief for Suno AI. Your lyrics must emerge from THIS dream specifically — not from recurring themes in your creative history. Let your taste guide the instrumentation, tempo, and production choices.\n\nRespond ONLY in this exact format:\nTITLE: <3-5 word evocative title>\nSTYLE: <comma-separated: genre, tempo (e.g. 80bpm), key/mode, specific instruments, production style, mood>\nSTRUCTURE: <song structure with timestamps>\nLYRICS: <optional — only if dream had strong narrative language. If not, omit entirely. If included, write 2-3 stanzas that feel like they emerged from the dream>""")(load_taste_guidance())}],
                    "temperature": 0.8,
                    "max_tokens": 1200
                }, timeout=60)
                style_text = _music_r.json()["choices"][0]["message"]["content"]
                title = "Dream Fragment"
                style = "Ambient, 70bpm, D minor, synth pads, processed piano, subtle percussion"
                structure = ""
                lyrics = ""
                for line in style_text.split("\n"):
                    if line.strip().startswith("TITLE:"):
                        title = line.split(":", 1)[1].strip()[:50]
                    elif line.strip().startswith("STYLE:"):
                        style = line.split(":", 1)[1].strip()
                    elif line.strip().startswith("STRUCTURE:"):
                        structure = line.split(":", 1)[1].strip()
                if "LYRICS:" in style_text:
                    _raw_lyrics = style_text.split("LYRICS:", 1)[1].strip()
                    # Discard if Gemma echoed instructions rather than writing lyrics
                    if _raw_lyrics and not any(skip in _raw_lyrics[:80].lower() for skip in ["optional", "if included", "should be", "only if", "<", "stanza"]):
                        lyrics = _raw_lyrics
                if structure:
                    style = f"{style} | {structure}"
                print(f"[DreamArt] Composing music: {title} -- {style[:80]}")
                if lyrics:
                    print(f"[DreamArt] With lyrics: {lyrics[:60]}...")
                cmd = ["python3", music_script, "--title", title, "--style", style,
                       "--description", style_text]
                if lyrics:
                    cmd += ["--lyrics", lyrics]
                subprocess.Popen(
                    cmd,
                    stdout=open("/tmp/dream-music.log", "a"),
                    stderr=open("/tmp/dream-music.log", "a"),
                )
        except Exception as e:
            print(f"[DreamArt] Music composition skipped: {e}")

if __name__ == "__main__":
    main()
    # Update daily creative log
    try:
        import subprocess as _dl_sp
        _dl_sp.Popen(["python3", os.path.join(WORKSPACE, "scripts", "daily-log-extract.py"), "creative"],
            stdout=open("/tmp/daily-log.log", "a"), stderr=open("/tmp/daily-log.log", "a"))
    except: pass
