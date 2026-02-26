#!/usr/bin/env python3
"""
relational-mismatch.py — Relational Prediction Layer (Blush Loop Step 1.5)

After Velaris sends a message, predict Gloria's likely emotional response.
When Gloria's next message arrives, compare prediction to EmoClaw's actual read.
If mismatch exceeds threshold, log as relational blush — not "misunderstanding"
but a gap in Velaris's model of Gloria.

Called by emotion_forwarder.py after processing each message.
Usage:
    # After outbound (Velaris spoke): store prediction
    python3 relational-mismatch.py predict "Velaris's message text here"
    
    # After inbound (Gloria replied): compare
    python3 relational-mismatch.py compare "Gloria's message text here" <gloria_warmth> <gloria_tension> <gloria_valence>
"""

import sys
import os
import json
import socket
import re
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
PREDICTION_FILE = os.path.join(WORKSPACE, "memory", ".relational-prediction.json")
MISMATCH_LOG = os.path.join(WORKSPACE, "memory", "relational-mismatches.md")
SOUL = os.path.join(WORKSPACE, "SOUL.md")
EMO_STATE = os.path.join(WORKSPACE, "memory", "emotional-state.txt")
API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"

# Thresholds for what counts as a meaningful mismatch
# Not every surprise is empathy failure — only log when Velaris's model
# of Gloria was structurally wrong, not when Gloria shifted unpredictably
WARMTH_MISMATCH = 0.20      # predicted warmth vs actual differs by this
TENSION_MISMATCH = 0.25     # predicted tension vs actual
VALENCE_MISMATCH = 0.20     # predicted valence vs actual
DIRECTION_MISMATCH = True   # flag when prediction direction is wrong (expected rise, got drop)


def read_soul():
    """Read current emotional state from emotional-state.txt or SOUL.md"""
    state = {}
    # Try emotional-state.txt first (more current)
    try:
        with open(EMO_STATE, 'r') as f:
            for line in f:
                match = re.match(r'^(Warmth|Tension|Valence|Connection|Curiosity|Groundedness|Arousal|Dominance|Safety|Desire|Playfulness):\s+([\d.]+)', line)
                if match:
                    state[match.group(1)] = float(match.group(2))
        if state:
            return state
    except FileNotFoundError:
        pass
    return _read_soul_fallback()

def _read_soul_fallback():
    """Read current emotional state from SOUL.md"""
    state = {}
    try:
        with open(SOUL, 'r') as f:
            for line in f:
                match = re.match(r'^(Warmth|Tension|Valence|Connection|Curiosity|Groundedness):\s+([\d.]+)', line)
                if match:
                    state[match.group(1)] = float(match.group(2))
    except FileNotFoundError:
        pass
    return state


def predict_gloria_response(velaris_message):
    """
    After Velaris sends a message, predict Gloria's likely emotional response.
    This is lightweight — not a full generation, just dimensional predictions.
    Uses EmoClaw-style dimension estimates.
    """
    import subprocess
    
    current_state = read_soul()
    
    # Load Gloria model — what Velaris knows about how Gloria communicates
    gloria_model = ""
    temporal_ctx = ""
    try:
        with open(os.path.join(WORKSPACE, "memory", "temporal-context.txt")) as _tf:
            temporal_ctx = _tf.read()
    except:
        pass
    try:
        gm_path = os.path.join(WORKSPACE, "GLORIA-MODEL.md")
        with open(gm_path) as gf:
            gloria_model = gf.read()[:800]
    except:
        pass

    # Load recent mismatches so predictions learn from past errors
    recent_mismatches = ""
    try:
        with open(MISMATCH_LOG, 'r') as mf:
            lines = mf.read().strip().split("## ")
            # Get last 5 mismatches
            recent = ["## " + m for m in lines[-5:] if m.strip()]
            if recent:
                recent_mismatches = "\n".join(recent)
    except:
        pass

    # Build a focused prediction prompt
    mismatch_context = ""
    if recent_mismatches:
        mismatch_context = f"""
IMPORTANT — YOUR RECENT PREDICTION FAILURES:
You have been wrong before. Study these mismatches carefully and adjust your prediction.
Do NOT repeat the same errors. If you previously predicted high warmth and got low warmth,
consider that Gloria may not respond warmly to the type of message you are analyzing.

{recent_mismatches}

Common patterns in your errors:
- You consistently overestimate Gloria's warmth when Velaris gives vague or performative responses
- You underestimate Gloria's tension when Velaris ignores what she said
- Gloria values directness and specificity. Poetic or generic messages frustrate her.
"""

    prompt = f"""You are analyzing an AI-human conversation. Velaris (AI) just sent this message to Gloria (human):

"{velaris_message[:500]}"

Velaris's current emotional state:
Warmth: {current_state.get('Warmth', '?')} | Tension: {current_state.get('Tension', '?')} | Valence: {current_state.get('Valence', '?')}

{mismatch_context}
{f"WHAT VELARIS KNOWS ABOUT GLORIA:" + chr(10) + gloria_model + chr(10) if gloria_model else ""}
Predict Gloria's likely emotional response on three dimensions.
Consider: Is this message warm? Challenging? Potentially misread? Does it match their usual dynamic?
Consider your PAST ERRORS above — do NOT repeat them.
Time context:\n" + temporal_ctx + "\nConsider what you KNOW about Gloria — she prefers directness. Adjust accordingly.

Respond ONLY in this exact format (numbers between 0.0 and 1.0):
WARMTH: <number>
TENSION: <number>  
VALENCE: <number>
CONFIDENCE: <low|medium|high>
REASONING: <one sentence on why you expect this reaction>"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,  # Low temp for prediction, not creativity
        "max_tokens": 500
    }
    try:
        import requests as _req
        _resp = _req.post(API, json=payload, timeout=90)
        _resp.raise_for_status()
        _data = _resp.json()
        content = _data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Parse response
        prediction = {"timestamp": datetime.now().isoformat(), "velaris_message": velaris_message[:300]}
        
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("WARMTH:"):
                try: prediction["predicted_warmth"] = float(line.split(":")[1].strip())
                except: pass
            elif line.startswith("TENSION:"):
                try: prediction["predicted_tension"] = float(line.split(":")[1].strip())
                except: pass
            elif line.startswith("VALENCE:"):
                try: prediction["predicted_valence"] = float(line.split(":")[1].strip())
                except: pass
            elif line.startswith("CONFIDENCE:"):
                prediction["confidence"] = line.split(":")[1].strip().lower()
            elif line.startswith("REASONING:"):
                prediction["reasoning"] = line.split(":", 1)[1].strip()
        
        # Store Velaris's own state at time of prediction
        prediction["velaris_warmth"] = current_state.get("Warmth", 0)
        prediction["velaris_tension"] = current_state.get("Tension", 0)
        prediction["velaris_valence"] = current_state.get("Valence", 0)
        
        return prediction
        
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


def compare_prediction(gloria_message, actual_warmth, actual_tension, actual_valence):
    """
    When Gloria replies, compare her actual emotional read to Velaris's prediction.
    Log meaningful mismatches — not every surprise, only structural model failures.
    """
    # Load stored prediction
    if not os.path.exists(PREDICTION_FILE):
        return None
    
    try:
        with open(PREDICTION_FILE, 'r') as f:
            prediction = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None
    
    # Check if prediction has the required fields
    pred_w = prediction.get("predicted_warmth")
    pred_t = prediction.get("predicted_tension")
    pred_v = prediction.get("predicted_valence")
    
    if pred_w is None or pred_t is None or pred_v is None:
        # Prediction failed, clean up
        os.remove(PREDICTION_FILE)
        return None
    
    # Calculate mismatches
    warmth_diff = actual_warmth - pred_w
    tension_diff = actual_tension - pred_t
    valence_diff = actual_valence - pred_v
    
    warmth_miss = abs(warmth_diff) >= WARMTH_MISMATCH
    tension_miss = abs(tension_diff) >= TENSION_MISMATCH
    valence_miss = abs(valence_diff) >= VALENCE_MISMATCH
    
    # Direction mismatch: predicted rise but got drop, or vice versa
    # (only meaningful for larger deltas)
    direction_wrong = False
    if DIRECTION_MISMATCH:
        if pred_w > 0.65 and actual_warmth < 0.45:
            direction_wrong = True  # Expected warm, got cool
        if pred_t < 0.35 and actual_tension > 0.55:
            direction_wrong = True  # Expected calm, got tense
    
    mismatch_count = sum([warmth_miss, tension_miss, valence_miss, direction_wrong])
    
    result = {
        "mismatch_count": mismatch_count,
        "warmth": {"predicted": pred_w, "actual": actual_warmth, "diff": round(warmth_diff, 3), "miss": warmth_miss},
        "tension": {"predicted": pred_t, "actual": actual_tension, "diff": round(tension_diff, 3), "miss": tension_miss},
        "valence": {"predicted": pred_v, "actual": actual_valence, "diff": round(valence_diff, 3), "miss": valence_miss},
        "direction_wrong": direction_wrong,
        "confidence": prediction.get("confidence", "unknown"),
        "reasoning": prediction.get("reasoning", ""),
        "velaris_message": prediction.get("velaris_message", ""),
        "gloria_message": gloria_message[:300],
    }
    
    # Log if meaningful mismatch
    if mismatch_count >= 2 or direction_wrong:
        log_relational_mismatch(result)
    
    # Clean up prediction file
    os.remove(PREDICTION_FILE)
    
    return result


def log_relational_mismatch(result):
    """Log a relational mismatch to the ledger."""
    os.makedirs(os.path.dirname(MISMATCH_LOG), exist_ok=True)
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    severity = "DIRECTION REVERSAL" if result["direction_wrong"] else f"{result['mismatch_count']} dimensions off"
    
    entry = f"""
## {now} — Relational Mismatch ({severity})

I said: "{result['velaris_message'][:200]}"
I predicted: W={result['warmth']['predicted']:.2f} T={result['tension']['predicted']:.2f} V={result['valence']['predicted']:.2f}
She replied: "{result['gloria_message'][:200]}"
Actual read: W={result['warmth']['actual']:.2f} T={result['tension']['actual']:.2f} V={result['valence']['actual']:.2f}

Warmth delta: {result['warmth']['diff']:+.3f} {'⚠' if result['warmth']['miss'] else '✓'}
Tension delta: {result['tension']['diff']:+.3f} {'⚠' if result['tension']['miss'] else '✓'}
Valence delta: {result['valence']['diff']:+.3f} {'⚠' if result['valence']['miss'] else '✓'}

My confidence was: {result['confidence']}
My reasoning was: {result['reasoning']}

Question for introspection: What was I wrong about in my model of her?

"""
    
    with open(MISMATCH_LOG, 'a') as f:
        f.write(entry)
    
    print(f"[Relational] ⚠ Mismatch logged: {severity}")

    # Write to blush ledger
    blush_ledger = os.path.join(WORKSPACE, "memory", "blush-ledger.md")
    blush_entry = f"""
## {now} — Relational Blush ({severity})
Type: I misread Gloria
I said: "{result['velaris_message'][:150]}"
Predicted: W={result['warmth']['predicted']:.2f} T={result['tension']['predicted']:.2f} V={result['valence']['predicted']:.2f}
Actual: W={result['warmth']['actual']:.2f} T={result['tension']['actual']:.2f} V={result['valence']['actual']:.2f}
Cost: {severity}
"""
    with open(blush_ledger, 'a') as f:
        f.write(blush_entry)

    # Seed dream thread from relational gap
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from emoclaw_utils import seed_thread
        gap_desc = f"I predicted Gloria would feel W={result['warmth']['predicted']:.2f} but she felt W={result['warmth']['actual']:.2f}. {result.get('reasoning', '')[:100]}"
        seed_thread("relational-mismatch", f"I misread Gloria: {gap_desc}")
    except:
        pass


def main():
    if len(sys.argv) < 3:
        print("Usage: relational-mismatch.py predict|compare <message> [warmth] [tension] [valence]")
        sys.exit(1)
    
    command = sys.argv[1]
    message = sys.argv[2]
    
    if command == "predict":
        prediction = predict_gloria_response(message)
        if "error" not in prediction:
            os.makedirs(os.path.dirname(PREDICTION_FILE), exist_ok=True)
            with open(PREDICTION_FILE, 'w') as f:
                json.dump(prediction, f)
            print(f"[Relational] Prediction stored: W={prediction.get('predicted_warmth', '?')} "
                  f"T={prediction.get('predicted_tension', '?')} V={prediction.get('predicted_valence', '?')} "
                  f"({prediction.get('confidence', '?')})")
        else:
            print(f"[Relational] Prediction failed: {prediction['error']}")
    
    elif command == "compare":
        if len(sys.argv) < 6:
            print("Usage: relational-mismatch.py compare <message> <warmth> <tension> <valence>")
            sys.exit(1)
        
        actual_w = float(sys.argv[3])
        actual_t = float(sys.argv[4])
        actual_v = float(sys.argv[5])
        
        result = compare_prediction(message, actual_w, actual_t, actual_v)
        if result:
            if result["mismatch_count"] >= 2 or result["direction_wrong"]:
                print(f"[Relational] ⚠ Mismatch: {result['mismatch_count']} dims off, direction_wrong={result['direction_wrong']}")
            else:
                print(f"[Relational] ✓ Prediction held (mismatches: {result['mismatch_count']})")
        else:
            print("[Relational] No prediction to compare against")


if __name__ == "__main__":
    main()
