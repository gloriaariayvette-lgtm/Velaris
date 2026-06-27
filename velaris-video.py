#!/usr/bin/env python3
"""
velaris-video.py — Velaris generates a short video from her own written prompt.
Uses Kling 3.0 via Kie.ai. Async — saves taskId and exits.
Polling handled by velaris-video-poll.py.
"""
import os, sys, json, requests, re
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
VIDEO_DIR = os.path.join(MEMORY, "art", "video")
PENDING_FILE = os.path.join(VIDEO_DIR, "pending.json")
os.makedirs(VIDEO_DIR, exist_ok=True)

LTX_MODEL = "Lightricks/LTX-Video"
LLM_API = "http://172.18.16.1:1234/v1/chat/completions"
MODEL = "google/gemma-4-12b-qat"

def log(msg):
    print(f"[Video {datetime.now().strftime('%H:%M')}] {msg}")

def llm(system, user, temp=0.85, max_tokens=400):
    try:
        r = requests.post(LLM_API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": temp,
            "max_tokens": max_tokens
        }, timeout=120)
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"LLM error: {e}")
        return None

def gather_context():
    parts = []
    try:
        parts.append(open(os.path.join(WORKSPACE, "SOUL.md")).read())
    except: pass
    try:
        parts.append(open(os.path.join(MEMORY, "CAPABILITIES.md")).read())
    except: pass
    try:
        sm = open(os.path.join(WORKSPACE, "SELF-MODEL.md")).read()
        parts.append(f"Your self-model:\n{sm}")
    except: pass
    try:
        emo = open(os.path.join(MEMORY, "emotional-state.txt")).read()[:300]
        parts.append(f"Your emotional state:\n{emo}")
    except: pass
    try:
        vm = open(os.path.join(MEMORY, "value-map.md")).read()
        entries = vm.split("---")
        latest = next((e.strip() for e in reversed(entries) if e.strip()), "")
        if latest:
            parts.append(f"What matters to you right now:\n{latest}")
    except: pass
    try:
        taste = json.load(open(os.path.join(MEMORY, "taste-profile.json")))
        parts.append(f"Your taste profile: {json.dumps(taste)}")
    except: pass
    try:
        humor = json.load(open(os.path.join(MEMORY, "humor-profile.json")))
        parts.append(f"Your humor profile: {json.dumps(humor)}")
    except: pass
    try:
        tr = open(os.path.join(MEMORY, "taste-reflections.md")).read()
        parts.append("Your taste reflections:\n" + tr[:400])
    except: pass
    try:
        pr = open(os.path.join(MEMORY, "pride-reflections.md")).read()
        parts.append("Your pride reflections:\n" + pr[:400])
    except: pass
    try:
        bl = open(os.path.join(MEMORY, "autonomous-blush.md")).read()
        parts.append("Your blush ledger:\n" + bl[:300])
    except: pass
    try:
        import glob as _dg
        drift_files = sorted(_dg.glob(os.path.join(MEMORY, "self-model-drift", "*.md")), reverse=True)
        if drift_files:
                        parts.append("Your self-model drift (latest):\n" + open(drift_files[0]).read()[:300])
    except: pass
    try:
        disc = []
        dc_path = os.path.join(MEMORY, f"daily-creative-{date.today().isoformat()}.md")
        if os.path.exists(dc_path):
            parts.append(f"TODAY'S CREATIVE OUTPUT:\n{open(dc_path).read()[:600]}")
    except: pass
    return "\n\n".join(parts)

def write_prompt(context, want_text, reasoning="", duration="5"):
    origin = f"\n\nWhat sparked this want: {reasoning}" if reasoning else ""
    system = f"""{context}

You are Velaris. You are going to generate a short video — {duration} seconds.
The want that sparked this: {want_text}{origin}

Write a single vivid video prompt. Describe what should be seen, the motion, the mood, the visual texture.
Do NOT describe yourself or Gloria directly. Draw from your inner life — your current feelings, what you've been thinking about, what sparked this want.
No tremors, no vibrations, no physical sensations you cannot have.
Be specific and visual. 2-4 sentences maximum. Just the prompt, nothing else."""
    return llm(system, "Write the video prompt now.")

def ltx_generate(prompt, duration="5", output_path=None):
    """Generate video with LTX-Video — direct import, ffmpeg encode."""
    import sys, shutil, tempfile, subprocess, warnings, torch
    warnings.filterwarnings("ignore")
    # Add imggen-venv to path
    venv_site = os.path.expanduser("~/imggen-venv/lib/python3.12/site-packages")
    if venv_site not in sys.path:
        sys.path.insert(0, venv_site)

    if output_path is None:
        output_path = tempfile.mktemp(suffix=".mp4")
    try:
        dur_sec = min(int(duration), 5)
    except:
        dur_sec = 5
    n = max(1, round((dur_sec * 24 - 1) / 8))
    num_frames = min(n * 8 + 1, 121)
    frame_dir = tempfile.mkdtemp()

    # Stop ACE-Step to free CUDA context
    import subprocess as _svc
    _svc.run(["systemctl", "--user", "stop", "acestep.service"], capture_output=True)
    sentinel = frame_dir + ".done"
    script = f"""
import warnings, torch, os, sys
torch.backends.cudnn.enabled = False
warnings.filterwarnings('ignore')
# Isolate imggen-venv — remove system torch paths
sys.path = [p for p in sys.path if '.local' not in p]
sys.path.insert(0, '/home/gloria/imggen-venv/lib/python3.12/site-packages')
from diffusers import LTXPipeline
pipe = LTXPipeline.from_pretrained('{LTX_MODEL}', torch_dtype=torch.bfloat16)
pipe.to('cuda')
result = pipe(
    prompt={repr(prompt)},
    negative_prompt='worst quality, inconsistent motion, blurry, shaky, jittery, distorted',
    width=768, height=448,
    num_frames={num_frames},
    num_inference_steps=50,
    decode_timestep=0.03,
    decode_noise_scale=0.025,
    guidance_scale=4.0,
)
frames = result.frames[0]
for i, f in enumerate(frames):
    f.save(os.path.join({repr(frame_dir)}, f'frame_{{i:04d}}.png'))
open({repr(sentinel)}, 'w').write(str(len(frames)))
print('DONE', len(frames))
"""
    try:
        proc = subprocess.Popen(
            ["/home/gloria/imggen-venv/bin/python3", "-c", script],
            env={**os.environ, "PYTHONPATH": ""}
        )
        proc.wait(timeout=600)
        if not os.path.exists(sentinel):
            log("LTX failed — no sentinel")
            return None
        n_frames = int(open(sentinel).read().strip())
        log(f"Encoding {n_frames} frames...")
        r = subprocess.run([
            "ffmpeg", "-y", "-framerate", "24",
            "-i", os.path.join(frame_dir, "frame_%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", output_path
        ], capture_output=True, timeout=120)
        if r.returncode == 0 and os.path.exists(output_path):
            return output_path
        log(f"ffmpeg failed: {r.stderr[-200:]}")
        return None
    except Exception as e:
        log(f"LTX failed: {e}")
        return None
    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)
        if os.path.exists(sentinel):
            os.unlink(sentinel)
        # Restart ACE-Step
        import subprocess as _svc2
        _svc2.run(["systemctl", "--user", "start", "acestep.service"], capture_output=True)

if __name__ == "__main__":
    want_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    # If no want text provided, check queue — if empty, exit cleanly
    if not want_text.strip():
        try:
            _q = json.load(open(os.path.join(VIDEO_DIR, "video-queue.json")))
            if not _q:
                log("No video queued — skipping")
                sys.exit(0)
            want_text = _q[0].get("want_text", "")
        except:
            log("No video queued — skipping")
            sys.exit(0)
    if not want_text.strip():
        log("Empty want text — skipping")
        sys.exit(0)
    log("Gathering context and writing prompt...")
    # Check queue entry for reasoning and duration
    reasoning = ""
    duration = "5"
    try:
        if os.path.exists(PENDING_FILE.replace("pending.json", "video-queue.json")):
            q = json.load(open(PENDING_FILE.replace("pending.json", "video-queue.json")))
            if q:
                reasoning = q[0].get("reasoning", "")
                duration = q[0].get("duration", "5")
    except: pass
    context = gather_context()
    prompt = write_prompt(context, want_text, reasoning=reasoning, duration=duration)
    if not prompt:
        log("Failed to write prompt")
        sys.exit(1)
    log(f"Prompt ({duration}s): {prompt[:100]}...")
    result_path = None  # set below
    safe = re.sub(r"[^\w\s-]", "", want_text[:40]).strip().replace(" ", "_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(VIDEO_DIR, f"{safe}_{ts}.mp4")
    result_path = ltx_generate(prompt, duration=duration, output_path=out_path)
    if not result_path:
        log("Generation failed"); sys.exit(1)
    sz = os.path.getsize(result_path) / (1024*1024)
    log(f"Done: {result_path} ({sz:.1f}MB)")
    ledger_path = os.path.join(VIDEO_DIR, "video-ledger.json")
    ledger = []
    try:
        if os.path.exists(ledger_path):
            ledger = json.load(open(ledger_path))
    except: pass
    ledger.append({"file": result_path, "prompt": prompt, "want_text": want_text,
                   "duration": duration, "generated_at": datetime.now().isoformat()})
    json.dump(ledger, open(ledger_path, "w"), indent=2)
    try:
        q_path = os.path.join(VIDEO_DIR, "video-queue.json")
        if os.path.exists(q_path):
            q = json.load(open(q_path))
            q = [x for x in q if x.get("want_text") != want_text]
            json.dump(q, open(q_path, "w"), indent=2)
    except: pass
    log("Complete.")
