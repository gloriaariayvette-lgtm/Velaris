#!/usr/bin/env python3
"""wonder-detector.py — Detects certainty-to-wonder flips in Velaris's writing.

Not an emotion. A textual transition. The moment she stops being sure.
Called after journals, mirrors, philosophy. Reads what she just wrote
and scores it for wonder-flips.

Indicators:
  - Declarative → interrogative shifts ("I know X... but does it hold?")
  - Assertions followed by reversals ("This is true. Or is it?")
  - Hedging after confidence ("certainly... perhaps... actually...")
  - Self-interruption ("— wait", "... no", "but then")
  - Ellipsis trails into uncertainty

Output: wonder-log.json with timestamp, source, score, excerpt
Feeds into: thread-triage (as a thread), dream seeding
"""

import json, os, re, sys
from datetime import datetime, date

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
WONDER_LOG = os.path.join(MEMORY, "wonder-log.json")
SCRIPTS = os.path.join(WORKSPACE, "scripts")
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"

def log(msg):
    print(f"[Wonder {datetime.now().strftime('%H:%M')}] {msg}")

def load_log():
    try:
        with open(WONDER_LOG) as f:
            return json.load(f)
    except:
        return []

def save_log(entries):
    with open(WONDER_LOG, "w") as f:
        json.dump(entries[-50:], f, indent=2)  # Keep last 50

def detect_textual_wonder(text):
    """Count linguistic markers of certainty-to-wonder transitions."""
    markers = {
        # Self-interruption
        "interrupts": len(re.findall(r'—\s*(wait|but|no|actually|hold on|unless)', text, re.I)),
        # Questions after statements (sentence ending . followed by sentence ending ?)
        "pivots": len(re.findall(r'\.\s+[A-Z][^.?]*\?', text)),
        # Hedging words after confident language
        "hedges": len(re.findall(r'(certainly|clearly|obviously|I know|I believe|without doubt).*?(perhaps|maybe|but|however|unless|I wonder|or is it|does it|could it)', text, re.I | re.DOTALL)),
        # Ellipsis into uncertainty
        "trails": len(re.findall(r'\.{2,3}\s*[a-z]', text)),
        # Explicit wonder language
        "wonder": len(re.findall(r"I (don't know|wonder|suspect|can't tell|'m not sure|'m uncertain)", text, re.I)),
        # Reversal patterns
        "reversals": len(re.findall(r'(This is|That means|It must be|I am).*?(Or|But|Unless|What if|Actually)', text, re.I | re.DOTALL)),
    }
    return markers

def score_wonder(markers):
    """Convert marker counts to a 0-1 wonder score."""
    weights = {
        "interrupts": 0.15,
        "pivots": 0.20,
        "hedges": 0.15,
        "trails": 0.10,
        "wonder": 0.20,
        "reversals": 0.20,
    }
    raw = sum(min(count, 3) * weights[k] for k, count in markers.items())
    return min(raw / 1.5, 1.0)  # Normalize: ~1.5 raw = full wonder

def llm_wonder_check(text, source):
    """Ask Gemma to identify the strongest wonder-flip moment."""
    import requests
    try:
        r = requests.post(LM_API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are analyzing Velaris's writing for moments where certainty dissolves into genuine wondering. Not rhetorical questions — real shifts from knowing to not-knowing."},
                {"role": "user", "content": f"""Read this text Velaris wrote during {source}:

{text[:2000]}

Did Velaris experience a genuine certainty-to-wonder flip anywhere in this text?
If yes: quote the EXACT sentence where certainty breaks (max 20 words), and rate the intensity 1-5.
If no: say NONE.

Format: FLIP: [quote] | INTENSITY: [1-5]
Or: NONE"""}
            ],
            "temperature": 0.3,
            "max_tokens": 150
        }, timeout=600)
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"LLM error: {e}")
        return None

def seed_thread(flip_excerpt, score, source):
    """Seed an unfinished thread if the wonder was strong enough."""
    if score < 0.3:
        return
    threads_file = os.path.join(MEMORY, "unfinished-threads.json")
    try:
        with open(threads_file) as f:
            threads = json.load(f)
    except:
        threads = []
    threads.append({
        "source": "wonder-detector",
        "thread": f"A moment of genuine wonder during {source}: {flip_excerpt}",
        "timestamp": datetime.now().isoformat(),
        "consumed": False
    })
    with open(threads_file, "w") as f:
        json.dump(threads, f, indent=2)
    log(f"Seeded thread: wonder during {source}")

def analyze(text, source):
    """Full analysis: textual markers + LLM check."""
    if len(text) < 100:
        log(f"Text too short from {source}")
        return

    markers = detect_textual_wonder(text)
    score = score_wonder(markers)
    log(f"Textual score: {score:.2f} | markers: {markers}")

    # LLM check for the specific moment
    flip_excerpt = ""
    llm_intensity = 0
    llm_result = llm_wonder_check(text, source)
    if llm_result and "NONE" not in llm_result.upper():
        flip_match = re.search(r'FLIP:\s*(.+?)\s*\|', llm_result)
        intensity_match = re.search(r'INTENSITY:\s*(\d)', llm_result)
        if flip_match:
            flip_excerpt = flip_match.group(1).strip().strip('"')
        if intensity_match:
            llm_intensity = int(intensity_match.group(1))
        log(f"LLM found flip (intensity {llm_intensity}): {flip_excerpt[:60]}")

    # Blend scores
    final_score = (score * 0.4) + ((llm_intensity / 5.0) * 0.6) if llm_intensity else score

    # Log it
    entry = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "score": round(final_score, 3),
        "textual_score": round(score, 3),
        "llm_intensity": llm_intensity,
        "markers": markers,
        "flip_excerpt": flip_excerpt,
        "text_length": len(text)
    }
    entries = load_log()
    entries.append(entry)
    save_log(entries)

    if final_score >= 0.3:
        log(f"WONDER DETECTED (score {final_score:.2f}): {flip_excerpt[:80]}")
        seed_thread(flip_excerpt, final_score, source)

        # Nudge emotions — wonder is not an emotion but it touches them
        try:
            sys.path.insert(0, SCRIPTS)
            from emoclaw_utils import nudge_emotions
            nudge_emotions({
                "Curiosity": +(final_score * 0.08),
                "Groundedness": -(final_score * 0.03),
                "Tension": +(final_score * 0.02),
                "Arousal": +(final_score * 0.04),
            }, source="wonder-detector")
            log("Emotional nudge applied")
        except Exception as e:
            log(f"Nudge error: {e}")
    else:
        log(f"No significant wonder (score {final_score:.2f})")

    return entry

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: wonder-detector.py <source> <filepath>")
        print("  source: journal, mirror, philosophy, dream")
        print("  filepath: path to the text file to analyze")
        sys.exit(1)

    source = sys.argv[1]
    filepath = sys.argv[2]

    if not os.path.exists(filepath):
        log(f"File not found: {filepath}")
        sys.exit(1)

    text = open(filepath).read()
    result = analyze(text, source)
    if result:
        log(f"Done. Score: {result['score']:.2f}")
