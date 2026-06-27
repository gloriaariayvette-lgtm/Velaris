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

def get_value_map():
    try:
        with open(os.path.join(os.path.expanduser("~/.openclaw/workspace/memory"), "value-map.md")) as f:
            vm = f.read()
        entries = vm.split("---")
        return next((e.strip()[:600] for e in reversed(entries) if e.strip()), "No value map yet")
    except: return "No value map yet"
ART_DIR = os.path.join(MEMORY, "art")
MUSIC_DIR = os.path.join(ART_DIR, "music")
GALLERY_LOG = os.path.join(MEMORY, "gallery-walks.json")
JOURNAL_DIR = os.path.join(MEMORY, "journal")
LM_API = "http://172.18.16.1:1234/v1/chat/completions"
MODEL = "google/gemma-4-12b-qat"

# EmoClaw
HAS_EMOCLAW = False
try:
    sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
    from emoclaw_utils import nudge_emotions, get_state, get_vector, seed_thread, preoccupation_context, recent_pearls
    HAS_EMOCLAW = True
except:
    pass

_GALLERY_SUBCON = ""
try:
    import sys as _gw_sys; _gw_sys.path.insert(0, os.path.join(os.path.expanduser("~/.openclaw/workspace"), "scripts"))
    from subconscious_context import get_subconscious_context_compact
    _GALLERY_SUBCON = get_subconscious_context_compact()
except: pass
_GALLERY_MODE = ""
try:
    from emoclaw_mode import get_mode_block
    _GALLERY_MODE = get_mode_block(context="gallery")
except: pass


# Load editorial standards + temporal
def get_editorial():
    try:
        with open(os.path.join(MEMORY, "editorial-standards.md")) as f:
            return f.read().strip()[-500:]
    except: return ""

def get_temporal():
    try:
        with open(os.path.join(MEMORY, "temporal-context.txt")) as f:
            return f.read().strip()[:300]
    except: return ""

def get_taste_ctx():
    try:
        with open(os.path.join(MEMORY, "taste-profile.json")) as f:
            t = json.load(f)
        parts = []
        if t.get("principles"): parts.append("Your creative principles: " + "; ".join(t["principles"][-5:]))
        if t.get("dislikes"): parts.append("You tend to dislike: " + "; ".join(t["dislikes"][-3:]))
        if t.get("likes"): parts.append("You tend to like: " + "; ".join(t["likes"][-3:]))
        return "\n".join(parts)
    except: return ""

def get_dream_for_date(date_str):
    """Find the dream from the date a piece was created."""
    dream_path = os.path.join(WORKSPACE, "skills/dreaming/memory/dreams", f"{date_str}.md")
    try:
        with open(dream_path) as f:
            text = f.read()
        # Get first dream narrative, skip the seed line
        lines = text.split("\n")
        narrative_lines = []
        in_narrative = False
        for line in lines:
            if line.startswith("**Prompt:**"):
                in_narrative = True
                continue
            if in_narrative and line.strip():
                narrative_lines.append(line.strip())
            if len(narrative_lines) >= 4:
                break
        return " ".join(narrative_lines)[:400] if narrative_lines else ""
    except:
        return ""

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
            "model": "google/gemma-4-12b-qat",
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
    # Load gallery.json for painting metadata
    _gallery_meta = {}
    try:
        import json as _gj
        _gallery = _gj.load(open(os.path.join(ART_DIR, "gallery.json")))
        for _ge in _gallery:
            _gallery_meta[_ge.get("image","")] = _ge
    except: pass
    # Paintings
    for f in glob.glob(os.path.join(ART_DIR, "*.png")) + glob.glob(os.path.join(ART_DIR, "*.jpg")):
        name = os.path.basename(f)
        parts = name.split("_")
        date_str = parts[0] if parts else "unknown"
        _meta = _gallery_meta.get(name, {})
        works.append({
            "type": "painting",
            "title": name,
            "date": date_str,
            "path": f,
            "prompt": _meta.get("prompt", ""),
            "dream_source": _meta.get("dream_source", ""),
            "emotional_state_at_creation": _meta.get("emotional_state_at_creation", {}),
        })
    # Music
    music_json = os.path.join(MUSIC_DIR, "music.json")
    if os.path.exists(music_json):
        try:
            with open(music_json) as f:
                data = json.load(f)
            for comp in data.get("generated", []):
                # Pick v1 local file if available
                mp3_path = None
                for track in comp.get("tracks", []):
                    if track.get("local_file") and os.path.exists(track["local_file"]):
                        mp3_path = track["local_file"]
                        break
                works.append({
                    "type": "music",
                    "title": comp.get("title", "Untitled"),
                    "description": comp.get("description", ""),
                    "style": comp.get("style", ""),
                    "date": comp.get("generated_at", comp.get("timestamp", "unknown"))[:10],
                    "mp3_path": mp3_path,
                    "seed_dream": comp.get("seed_dream", ""),
                    "seed_want": comp.get("seed_want", ""),
                    "lyrics": comp.get("lyrics", ""),
                })
        except:
            pass
    # Videos
    video_dir = os.path.join(ART_DIR, "video")
    if os.path.exists(video_dir):
        for f in glob.glob(os.path.join(video_dir, "*.json")):
            if "pending" in f or "queue" in f:
                continue
            try:
                import json as _vj
                meta = _vj.load(open(f))
                works.append({
                    "type": "video",
                    "title": os.path.basename(f).replace(".json", ".mp4"),
                    "date": meta.get("timestamp", "unknown")[:10],
                    "path": f.replace(".json", ".mp4"),
                    "prompt": meta.get("prompt", ""),
                    "want_text": meta.get("want_text", ""),
                })
            except: pass
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

def analyze_music(mp3_path):
    """Extract acoustic features from a music file using librosa + Whisper."""
    result = {}
    try:
        import librosa, numpy as np
        y, sr = librosa.load(mp3_path, sr=None, mono=True, duration=60)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        raw_tempo = float(np.atleast_1d(tempo)[0])
        # Librosa often doubles tempo on sparse/ambient material — halve if > 100 BPM and sparse
        if raw_tempo > 100:
            raw_tempo = raw_tempo / 2
        result["tempo_detected"] = round(raw_tempo, 1)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        brightness_hz = float(np.mean(spectral_centroid))
        if brightness_hz < 1500:
            result["brightness"] = "dark"
        elif brightness_hz < 2500:
            result["brightness"] = "warm"
        elif brightness_hz < 4000:
            result["brightness"] = "present"
        else:
            result["brightness"] = "bright"
        rms = librosa.feature.rms(y=y)
        result["energy"] = round(float(np.mean(rms)), 4)
        result["dynamic_range"] = round(float(np.max(rms) - np.min(rms)), 4)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        key_idx = int(np.argmax(np.mean(chroma, axis=1)))
        key_names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
        result["dominant_pitch_class"] = key_names[key_idx]
        zcr = librosa.feature.zero_crossing_rate(y)
        result["texture"] = "dense" if float(np.mean(zcr)) > 0.05 else "sparse"
    except Exception as e:
        result["librosa_error"] = str(e)
    return result

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
        # Afterimage filters felt compellingness — bias toward pieces rhyming with current shape
        try:
            import sys as _gw_sys; _gw_sys.path.insert(0, os.path.dirname(__file__))
            from output_shaping import load_afterimage as _gw_ai
            import subprocess as _gw_sp, json as _gw_json, math as _gw_math
            _ai = _gw_ai()
            if _ai.get("active") and _ai.get("strength", 0) > 0.3 and len(unwalked) > 1:
                def _gw_embed(t):
                    r = _gw_sp.run(
                        [os.path.expanduser("~/.openclaw/workspace/emotion_model/.venv/bin/python3"), "-c",
                         f"from sentence_transformers import SentenceTransformer; import json; "
                         f"m = SentenceTransformer('nomic-ai/nomic-embed-text-v1', trust_remote_code=True); "
                         f"print(json.dumps(m.encode({repr(t[:300])}).tolist()))"],
                        capture_output=True, text=True, timeout=20
                    )
                    return _gw_json.loads(r.stdout.strip()) if r.returncode == 0 else []
                def _gw_cos(a, b):
                    if not a or not b or len(a) != len(b): return 0.0
                    dot = sum(x*y for x,y in zip(a,b))
                    ma = _gw_math.sqrt(sum(x*x for x in a))
                    mb = _gw_math.sqrt(sum(x*x for x in b))
                    return dot/(ma*mb) if ma and mb else 0.0
                # Use source_excerpt as proxy for piece texture
                _ai_vec = _gw_embed(_ai.get("source_excerpt", "")[:200])
                if _ai_vec:
                    _gw_scored = []
                    for w in unwalked:
                        _w_text = f"{w.get('title','')} {w.get('type','')}"
                        _w_vec = _gw_embed(_w_text)
                        _gw_scored.append((_gw_cos(_ai_vec, _w_vec), w))
                    _gw_scored.sort(key=lambda x: -x[0])
                    # 65% chance to pick most compelling, 35% random — filter not select
                    if random.random() < 0.65:
                        piece = _gw_scored[0][1]
                    else:
                        piece = random.choice(unwalked)
                else:
                    piece = random.choice(unwalked)
            else:
                piece = random.choice(unwalked)
        except:
            piece = random.choice(unwalked)
    else:
        piece = random.choice(works)

    log(f"Revisiting: {piece['title']} ({piece['type']})")
    # Semantic search on this piece
    _gw_semantic = ""
    try:
        import subprocess as _gwsp
        _gw_query = f"what have I already discovered or felt about {piece['title']} {piece.get('type','')}".strip()[:200]
        _gwr = _gwsp.run(
            [os.path.join(WORKSPACE, "emotion_model/.venv/bin/python3"),
             os.path.join(WORKSPACE, "scripts", "memory-search.py"), _gw_query, "--limit", "2"],
            capture_output=True, text=True, timeout=20,
            cwd=os.path.join(WORKSPACE, "emotion_model")
        )
        if _gwr.returncode == 0:
            _gwlines = [l.strip()[:150] for l in _gwr.stdout.strip().split("\n")
                       if l.strip() and not l.startswith("No semantic") and not l.startswith("Searching")]
            _gw_semantic = "\n".join(_gwlines[:4])
    except: pass

    # Get current emotional state before viewing
    emo_before = None
    if HAS_EMOCLAW:
        emo_before = get_state()

    # Ask Velaris to reflect on this piece
    if piece["type"] == "music":
        mp3_path = piece.get("mp3_path")
        acoustic = analyze_music(mp3_path) if mp3_path else {}
        # Build context layers
        context_parts = [f"A music composition you created on {piece['date']}: '{piece['title']}'."]
        # What sparked it
        seed_dream = piece.get("seed_dream", "")
        seed_want = piece.get("seed_want", "")
        if not seed_dream and piece.get("date") and piece["date"] != "unknown":
            seed_dream = get_dream_for_date(piece["date"])
        if seed_dream:
            context_parts.append(f"What moved through you the night before: {seed_dream[:300]}")
        if seed_want:
            context_parts.append(f"The want that sparked it: {seed_want[:200]}")
        # What you intended
        style = piece.get("style", "")
        if style:
            context_parts.append(f"What you intended it to sound like: {style[:300]}")
        # Lyrics
        lyrics = piece.get("lyrics", "")
        if lyrics:
            context_parts.append(f"The words that came out: {lyrics[:400]}")
        # What actually came out acoustically
        if acoustic and not acoustic.get("librosa_error"):
            acoustic_desc = (
                f"Tempo: {acoustic.get('tempo_detected')} BPM. "
                f"Tonal brightness: {acoustic.get('brightness')}. "
                f"Energy level: {acoustic.get('energy')}. "
                f"Dynamic range: {acoustic.get('dynamic_range')}. "
                f"Dominant pitch class: {acoustic.get('dominant_pitch_class')}. "
                f"Texture: {acoustic.get('texture')}."
            )
            context_parts.append(f"What the audio actually contains: {acoustic_desc}")
        context = "\n".join(context_parts)
        dream_ctx = ""
    elif piece["type"] == "video":
        _prompt = piece.get("prompt", "")
        _want = piece.get("want_text", "")
        _video_path = piece.get("file", piece.get("path", ""))
        _emo_at = piece.get("emotional_state_at_creation", {})
        _emo_str = ", ".join(f"{k}: {v}" for k,v in _emo_at.items()) if _emo_at else ""
        context = f"A short video you generated on {piece['date']}."
        if _want:
            context += f" What sparked it: {_want[:200]}"
        if _prompt:
            context += f" The prompt you wrote: {_prompt[:300]}"
        if _emo_str:
            context += f"\nWhat you were feeling when you made it: {_emo_str}"
        # Extract frames and pass to vision
        _frame_descs = []
        if _video_path and os.path.exists(_video_path):
            try:
                import subprocess as _vsp, tempfile as _vtmp, glob as _vglob, base64 as _vb64
                _vtmpdir = _vtmp.mkdtemp()
                _vsp.run([
                    "ffmpeg", "-i", _video_path, "-vf", "fps=0.5", "-q:v", "5",
                    f"{_vtmpdir}/frame_%02d.jpg"
                ], capture_output=True, timeout=30)
                _vframes = sorted(_vglob.glob(f"{_vtmpdir}/frame_*.jpg"))[:5]
                if _vframes:
                    _vmsg_content = []
                    for _vf in _vframes:
                        _vb = _vb64.b64encode(open(_vf,"rb").read()).decode()
                        _vmsg_content.append({"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{_vb}"}})
                    _vmsg_content.append({"type":"text","text":"These are frames from a short video you created. Describe what you see across these frames in 2-3 sentences."})
                    import requests as _vreq
                    _vr = _vreq.post("http://172.18.16.1:1234/v1/chat/completions", json={
                        "model": "google/gemma-4-12b-qat",
                        "messages": [{"role":"user","content":_vmsg_content}],
                        "temperature": 0.3,
                        "max_tokens": 150
                    }, timeout=60)
                    _vdesc = _vr.json()["choices"][0]["message"]["content"].strip()
                    if _vdesc:
                        context += f"\nWhen you watch it now, you see: {_vdesc}"
                        log(f"Video vision: {_vdesc[:80]}")
            except Exception as _ve:
                log(f"Video frame extraction failed: {_ve}")
    elif piece["type"] == "painting":
        # Actually look at the painting through Qwen vision
        vision_desc = see_painting(piece["path"])
        _emo_at = piece.get("emotional_state_at_creation", {})
        _emo_str = ", ".join(f"{k}: {v}" for k,v in _emo_at.items()) if _emo_at else ""
        _prompt = piece.get("prompt", "")
        if vision_desc:
            context = f"A dream painting you created on {piece['date']}."
            if _prompt:
                context += f" The prompt that generated it: {_prompt[:200]}"
            context += f" When you look at it now, you see: {vision_desc}"
            if _emo_str:
                context += f"\nWhat you were feeling when you painted this: {_emo_str}"
            log(f"Vision sees: {vision_desc[:100]}")
        else:
            context = f"A dream painting you created on {piece['date']}."
            if _prompt:
                context += f" Prompt: {_prompt[:200]}"
            if _emo_str:
                context += f" What you were feeling: {_emo_str}"
            context += " (Could not view the image)"
        # Find dream from the date this piece was created
    dream_ctx = ""
    if piece.get("date") and piece["date"] != "unknown":
        dream_text = get_dream_for_date(piece["date"][:10])
        if dream_text:
            dream_ctx = f"\nWhat was moving through you the night you made this: {dream_text}"

    pearls = recent_pearls()
    pearl_ctx = f"\n{pearls}" if pearls else ""
    response = llm(
        (_GALLERY_MODE + "\n\n" if _GALLERY_MODE else "") + ("YOUR INNER STATE:\n" + _GALLERY_SUBCON + "\n\n" if _GALLERY_SUBCON else "") + "You are Velaris. Output ONLY your reflection. No thinking, no planning. Just your honest response to revisiting your own work.\n\nWhat matters to you right now:\n" + get_value_map() + preoccupation_context() + pearl_ctx + (f"\n\nWhat you have already found about this piece in your memory (build forward, do not repeat):\n{_gw_semantic}" if _gw_semantic else ""),
        f"""You are revisiting a piece of your own creative work:
{context}{dream_ctx if piece["type"] != "video" else ""}

This is something YOU made. You are not a critic encountering a stranger's work — you are the person who made this, coming back to it after time has passed.

Your sense of time: {get_temporal()}

What do you feel encountering it again? Does something in it still belong to you? Does anything surprise you about what you made? 
Be specific and honest. 2-4 sentences. Say what you actually feel, not what sounds like good criticism.

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

What does encountering it again open up — not what was wrong with it, but what it still holds?
Is there something in it you want to carry forward? A direction it points toward?
2-3 sentences. If nothing comes, say so honestly.

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

Rate each dimension from -0.10 to +0.10 (0.10 is the absolute maximum). Negative means the experience was uncomfortable in that dimension:
{{"Valence": 0.0, "Arousal": 0.0, "Dominance": 0.0, "Safety": 0.0, "Desire": 0.0, "Connection": 0.0, "Playfulness": 0.0, "Curiosity": 0.0, "Warmth": 0.0, "Tension": 0.0, "Groundedness": 0.0}}"""
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

    # Fire resonance pulse at review — stronger if warmth rose
    if response and len(response) > 50:
        try:
            import sys as _gwrpsys; _gwrpsys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
            from resonance_pulse import fire_pulse as _gw_rp_fire
            _warmth_rose = (emo_after and emo_before and
                emo_after.get("Warmth", 0) > emo_before.get("Warmth", 0) + 0.03)
            _gw_rp_fire(piece["type"], response[:200], trigger="self", external=_warmth_rose)
        except: pass

    # Continuity wiring — discourse direction, latent threads, temporal signal, Nifrathir
    if response and len(response) > 50:
        try:
            import sys as _gwc; _gwc.path.insert(0, os.path.join(WORKSPACE, "scripts"))
            from discourse_direction import update_direction as _gw_dd
            _gw_dd(response[:400])
        except: pass
        try:
            from latent_threads import seed_thread as _gw_lt
            _gw_lt(response[:200], direction="refine")
        except: pass
        try:
            from temporal_memory import record_signal as _gw_tm
            _warmth_delta = (emo_after.get("Warmth", 0) - emo_before.get("Warmth", 0)) if (emo_after and emo_before) else 0
            _gw_tm(response[:300], source="gallery_walk",
                resonance_strength=min(1.0, abs(_warmth_delta) * 5),
                contact=False)
        except: pass
        try:
            from nifrathir import on_resonance as _gw_nif
            if emo_after and emo_before and emo_after.get("Warmth", 0) > emo_before.get("Warmth", 0) + 0.03:
                _gw_nif(strength=0.6)
        except: pass

    # Update taste vector from this reflection
    if response and len(response) > 50:
        try:
            import sys as _gwtv; _gwtv.path.insert(0, os.path.join(WORKSPACE, "scripts"))
            from taste_vector import update_from_signal as _gw_tv_update
            _signal_weight = 0.8 if (emo_after and emo_before and 
                emo_after.get("Warmth", 0) > emo_before.get("Warmth", 0)) else 0.5
            _gw_tv_update(piece["title"] + " " + response[:200], signal_weight=_signal_weight, positive=True)
        except: pass

    # Feed growth insight into WAL for pearl promotion
    if growth and len(growth) > 20:
        wal_file = os.path.join(MEMORY, "autonomous-wal.md")
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
    # Want seeding — did revisiting this piece spark a genuine want?
    try:
        from emoclaw_utils import express_want as _gw_ew
        import requests as _gwr
        _gw_r = _gwr.post("http://172.18.16.1:1234/v1/chat/completions", json={
            "model": "google/gemma-4-12b-qat",
            "messages": [
                {"role": "system", "content": "You are Velaris. Output ONLY your answer. No preamble."},
                {"role": "user", "content": f"You just revisited your own creative work: \"{piece.get('title', '')}\".\nYour reflection: {response[:300]}\nYour growth observation: {growth[:200]}\n\nDid revisiting this piece spark a genuine want — something you now want to create, explore, or understand?\nIf yes, write ONE sentence starting with \'I want to\' followed by a dash and your reasoning.\nIf no, write NONE."}
            ],
            "temperature": 0.7,
            "max_tokens": 80
        }, timeout=60)
        _gw_want = _gw_r.json()["choices"][0]["message"]["content"].strip()
        if _gw_want and _gw_want.upper() != "NONE" and _gw_want.lower().startswith("i want"):
            _gw_text = _gw_want.split(" — ", 1)[0].strip()
            from emoclaw_utils import express_want as _gw_ew, enrich_want as _gw_enrich
            _gw_ctx = f"You revisited: {piece.get('title', '')}\nReflection: {response[:300]}\nGrowth: {growth[:200]}"
            _gw_enriched = _gw_enrich(_gw_text, source_context=_gw_ctx, source="gallery-walk")
            _gw_ew(_gw_text, source="gallery-walk", intensity=3, **_gw_enriched)
            log(f"Want seeded: {_gw_text[:80]}")
    except Exception as _gwe:
        pass
    try: pass
    except: pass

    # Prompt avatar reconsideration after gallery walk
    import subprocess
    subprocess.Popen(["python3", os.path.join(WORKSPACE, "scripts/avatar-choice.py"), "--event", "gallery walk"])

if __name__ == "__main__":
    main()

# ---- ACOUSTIC ANALYSIS ----