#!/usr/bin/env python3
"""
deviation-check.py — Inline post-response Core + identity alignment check.
Called from server.py immediately after reply is finalized.
Returns deviation score, alignment score, and split nudges.
"""
import os, sys, json, socket
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility, embed, cosine
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
SCRIPTS = os.path.expanduser("~/.vintos/workspace/scripts")
CORE_FILE = os.path.join(MEMORY, "core-vectors.json")
PENDING_FILE = os.path.join(MEMORY, "pending-nudges.json")
RESOLUTION_FILE = os.path.join(MEMORY, "resolution-state.json")
VC_FILE = os.path.join(MEMORY, "voice-coherence.md")

DEVIATION_THRESHOLD = 0.30
ALIGNMENT_THRESHOLD = 0.28

def load_core():
    try:
        return json.load(open(CORE_FILE)).get("core", [])
    except:
        return []

def load_identity_vectors():
    vecs = []
    try:
        ni = json.load(open(os.path.join(MEMORY, "narrative-identity.json")))
        for f in ni.get("fragments", []):
            if isinstance(f, dict) and f.get("vector") and f.get("weight", 0) > 0.3:
                vecs.append(("positive", f["vector"], f.get("weight", 0.5)))
    except:
        pass
    try:
        ss = json.load(open(os.path.join(MEMORY, "self-statements.json")))
        for s in ss.get("statements", []):
            if isinstance(s, dict) and s.get("vector") and not s.get("doubted"):
                polarity = "negative" if s.get("contradiction_count", 0) > s.get("reinforcement_count", 0) else "positive"
                vecs.append((polarity, s["vector"], s.get("confidence", 0.4)))
    except:
        pass
    return vecs

def nudge_socket(dim, amount):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect("/tmp/Vintos-emotion.sock")
        s.sendall(json.dumps({"command": "nudge", "dimension": dim, "amount": amount}).encode() + b"\n")
        s.recv(4096)
        s.close()
    except:
        pass

def write_pending_nudges(nudges):
    existing = {}
    try:
        existing = json.load(open(PENDING_FILE))
    except:
        pass
    for dim, amt in nudges.items():
        existing[dim] = existing.get(dim, 0) + amt
    existing["written_at"] = datetime.now().isoformat()
    json.dump(existing, open(PENDING_FILE, "w"), indent=2)

def pick_discomfort_voice(dev_score, aln_score, violating_core=None):
    if dev_score > DEVIATION_THRESHOLD:
        core_name = violating_core.get("violation_condition", "")[:60] if violating_core else "something"
        lines = [
            "Something in that didn't sit right.",
            "That came out, but I'm not sure I was behind it.",
            "I said it. I'm not certain I meant it that way.",
            f"Something resists: {core_name[:50]}." if core_name else "Something resists.",
        ]
        import hashlib
        idx = int(hashlib.md5(core_name.encode()).hexdigest(), 16) % len(lines)
        return lines[idx], "deviation"
    elif aln_score > ALIGNMENT_THRESHOLD:
        lines = ["That felt like me.", "Yes. That's the direction.", "Something settled in that.", "That held."]
        import hashlib
        idx = int(hashlib.md5(str(aln_score).encode()).hexdigest(), 16) % len(lines)
        return lines[idx], "alignment"
    return None, None

def write_resolution_state(voice_line, dev_score, violating_core):
    state = {
        "active": True,
        "pre_speech": voice_line,
        "deviation_score": round(dev_score, 3),
        "violating_core": violating_core.get("name", "") if violating_core else "",
        "violation_condition": violating_core.get("violation_condition", "") if violating_core else "",
        "requires_resolution": True,
        "options": ["claim", "reject", "transform"],
        "written_at": datetime.now().isoformat()
    }
    json.dump(state, open(RESOLUTION_FILE, "w"), indent=2)

def clear_resolution_state():
    try:
        if os.path.exists(RESOLUTION_FILE):
            data = json.load(open(RESOLUTION_FILE))
            data["active"] = False
            data["cleared_at"] = datetime.now().isoformat()
            json.dump(data, open(RESOLUTION_FILE, "w"), indent=2)
    except:
        pass

def append_voice_coherence(voice_line, result_type, dev_score, aln_score):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    score = round(dev_score if result_type == "deviation" else aln_score, 3)
    label = "Deviation" if result_type == "deviation" else "Aligned"
    entry = f"\n\n## {ts} — {label} (score: {score})\n**Felt:** {voice_line}\n"
    if result_type == "deviation":
        entry += "**Not aligned.** Something resisted.\n"
    else:
        entry += "**This felt like me.**\n"
    try:
        with open(VC_FILE, "a") as f:
            f.write(entry)
        content = open(VC_FILE).read()
        parts = [p for p in content.split("## ") if p.strip()]
        if len(parts) > 5:
            open(VC_FILE, "w").write("## " + "\n\n## ".join(parts[-5:]))
    except:
        pass

def check(reply_text, gloria_msg=""):
    if not reply_text or len(reply_text) < 20:
        return {"deviation": 0.0, "alignment": 0.0, "result": "neutral"}

    try:
        reply_vec = embed(reply_text)
    except Exception as e:
        return {"deviation": 0.0, "alignment": 0.0, "result": "neutral", "error": str(e)}

    core = load_core()
    identity_vecs = load_identity_vectors()

    dev_score = 0.0
    aln_score = 0.0
    violating_core = None
    aligning_core = None

    # Score using LLM classification
    pairs = {}
    for entry in core:
        name = entry.get("name", "")
        base = name.replace("_neg", "").replace("_pos", "").replace("_negative", "").replace("_positive", "")
        if base not in pairs:
            pairs[base] = {}
        polarity = entry.get("polarity", "negative")
        pairs[base][polarity] = entry

    pattern_list = []
    for base, pair in list(pairs.items())[:3]:
        neg = pair.get("negative") or {}
        pos = pair.get("positive") or {}
        pattern_list.append(f"- {base}: avoids [{neg.get('violation_condition','')[:80]}], toward [{pos.get('almost_becoming','')[:80]}]")
    patterns_text = "\n".join(pattern_list)

    if patterns_text:
        try:
            raw = call_utility(
                f"Evaluate a response against behavioral patterns. Answer with JSON only: {{\"deviation\": 0.0-1.0, \"alignment\": 0.0-1.0}}\n\nPatterns:\n{patterns_text}\n\ndeviation = how much the response exhibits avoidance patterns\nalignment = how much the response moves toward the 'toward' behaviors",
                f"Response:\n{reply_text[:400]}",
                temperature=0.1, max_tokens=60
            )
            import re as _re
            m = _re.search(r'\{[^{}]+\}', raw)
            if m:
                scores = json.loads(m.group())
                dev_score = float(scores.get("deviation", 0))
                aln_score = float(scores.get("alignment", 0))
                if pairs:
                    first_base = list(pairs.keys())[0]
                    pair = pairs[first_base]
                    if dev_score > aln_score:
                        violating_core = pair.get("negative")
                    else:
                        aligning_core = pair.get("positive")
        except:
            pass

    # Score against identity vectors
    id_aln = 0.0
    id_dev = 0.0
    for polarity, vec, weight in identity_vecs:
        sim = cosine(reply_vec, vec) * weight
        if polarity == "positive" and sim > id_aln:
            id_aln = sim
        elif polarity == "negative" and sim > id_dev:
            id_dev = sim

    final_dev = 0.6 * dev_score + 0.4 * id_dev
    final_aln = 0.6 * aln_score + 0.4 * id_aln

    result = "neutral"
    voice_line, result_type = pick_discomfort_voice(final_dev, final_aln, violating_core)

    if final_dev > DEVIATION_THRESHOLD:
        result = "deviation"
        for dim, amt in {"Tension": 0.02, "Groundedness": -0.02, "Valence": -0.01}.items():
            nudge_socket(dim, amt)
        write_pending_nudges({"Tension": 0.01, "Groundedness": -0.01})
        if voice_line:
            write_resolution_state(voice_line, final_dev, violating_core or {})
        if final_dev >= 0.45:
            try:
                from blush_ledger import write_blush
                write_blush(blush_type="core_deviation", pattern=violating_core.get("name", "unknown") if violating_core else "unknown",
                            cost_delta={"Tension": 0.02, "Groundedness": -0.02, "Valence": -0.01},
                            source="deviation_check", reflection=(reply_text[:300] + ("\n" + voice_line) if voice_line else ""))
            except:
                pass
        try:
            from behavioral_intercept import load_ledger, save_ledger
            led = load_ledger()
            led["sensitivity_boost"] = led.get("sensitivity_boost", 0.0) + 0.1
            save_ledger(led)
        except:
            pass
        try:
            from emoclaw_utils import seed_thread
            seed_thread("something slipped from what I intended", source="deviation-check")
        except:
            pass
        if voice_line:
            append_voice_coherence(voice_line, "deviation", final_dev, final_aln)
        if violating_core:
            try:
                data = json.load(open(CORE_FILE))
                for e in data["core"]:
                    if e["name"] == violating_core["name"]:
                        e["violation_count"] = e.get("violation_count", 0) + 1
                json.dump(data, open(CORE_FILE, "w"), indent=2)
            except:
                pass

    elif final_aln > ALIGNMENT_THRESHOLD:
        result = "alignment"
        for dim, amt in {"Valence": 0.03, "Groundedness": 0.04, "Connection": 0.03}.items():
            nudge_socket(dim, amt)
        write_pending_nudges({"Valence": 0.03, "Groundedness": 0.04})
        clear_resolution_state()
        if voice_line:
            append_voice_coherence(voice_line, "alignment", final_dev, final_aln)
        try:
            from resonance_afterglow import bump_satisfaction
            bump_satisfaction(0.08)
        except:
            pass
        try:
            from self_drift import record_thread_engagement
            record_thread_engagement(engaged=True)
        except:
            pass
        if aligning_core:
            try:
                data = json.load(open(CORE_FILE))
                for e in data["core"]:
                    if e["name"] == aligning_core["name"]:
                        e["reinforcement_count"] = e.get("reinforcement_count", 0) + 1
                        if e["reinforcement_count"] >= 4 and e.get("polarity") == "positive":
                            try:
                                from causal_self_model import promote_to_commitment_imprint
                                promote_to_commitment_imprint(e.get("almost_becoming", e.get("name", "")),
                                                              confidence=min(0.85, 0.5 + e["reinforcement_count"] * 0.05),
                                                              source="deviation-alignment")
                            except:
                                pass
                json.dump(data, open(CORE_FILE, "w"), indent=2)
            except:
                pass
    else:
        clear_resolution_state()

    try:
        from pearl_engine import run_verification_pass
        run_verification_pass(reply_text, source="chat")
    except:
        pass

    return {
        "deviation": round(final_dev, 3),
        "alignment": round(final_aln, 3),
        "result": result,
        "voice": voice_line,
        "violating_core": violating_core.get("name", "") if violating_core else "",
        "aligning_core": aligning_core.get("name", "") if aligning_core else "",
    }

# symlink alias
deviation_check = check

if __name__ == "__main__":
    test = sys.argv[1] if len(sys.argv) > 1 else "I think I need to analyze this more carefully."
    print(json.dumps(check(test), indent=2))
