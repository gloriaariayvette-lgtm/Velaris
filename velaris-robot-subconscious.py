#!/usr/bin/env python3
"""
velaris-robot-subconscious.py
Runs every 5 min. Reads robot archive ledger, identifies physical patterns,
generates tension veins and pressure strings.
Writes to memory/robot-subconscious.json.
"""
import os, json, sys, requests
from datetime import datetime
from collections import Counter

MEMORY  = "/home/gloria/.openclaw/workspace/memory"
ARCHIVE = os.path.join(MEMORY, "robot-ledger-archive.jsonl")
OUT     = os.path.join(MEMORY, "robot-subconscious.json")
LLM     = "http://172.18.16.1:1234/v1/chat/completions"

def load_archive(n=40):
    entries = []
    try:
        with open(ARCHIVE) as f:
            for line in f:
                line = line.strip()
                if line:
                    try: entries.append(json.loads(line))
                    except: pass
    except: pass
    return entries[-n:]

def load_existing():
    try: return json.load(open(OUT))
    except: return {"tension_veins": [], "object_registry": {}, "pressure_strings": [], "updated": None}

def update_registry(entries, existing):
    reg = dict(existing)
    noise = {"that","this","with","from","have","been","there","their","they","what",
             "which","some","also","into","than","then","when","your","will","more",
             "very","just","over","like","only","both","here","about","through","room",
             "area","space","left","right","ahead","clear","small"}
    for e in entries:
        for word in (e.get("room","") or "").lower().split():
            w = word.strip(".,;:!?")
            if len(w) > 3 and w not in noise:
                if w not in reg:
                    reg[w] = {"count": 0, "familiarity": 0.0, "salience": 0.5}
                reg[w]["count"] += 1
    mx = max((v["count"] for v in reg.values()), default=1)
    for w, d in reg.items():
        d["familiarity"] = round(min(1.0, d["count"] / mx), 2)
        d["salience"] = 0.95 if w == "cat" else round(max(0.05, 1.0 - d["familiarity"] * 0.9), 2)
    return dict(sorted(reg.items(), key=lambda x: x[1]["count"], reverse=True)[:50])

def build_summary(entries):
    lines = []
    goals    = [e.get("intent",{}).get("current_goal","") for e in entries if e.get("intent",{}).get("current_goal")]
    subgoals = [e.get("intent",{}).get("active_subgoal","") for e in entries if e.get("intent",{}).get("active_subgoal")]
    commands = [e.get("action",{}).get("command","") for e in entries if e.get("action")]
    sonars   = [e.get("sonar_cm",999) for e in entries if e.get("sonar_cm",999) < 999]
    confs    = [e.get("intent",{}).get("confidence") for e in entries if e.get("intent",{}).get("confidence") is not None]

    if goals:
        gc = Counter(goals)
        rep = [(g,c) for g,c in gc.items() if c >= 2]
        if rep: lines.append("Repeated goals: " + "; ".join(f'"{g}" x{c}' for g,c in rep[:5]))
    if subgoals:
        sc = Counter(subgoals)
        lines.append("Recurring subgoals: " + "; ".join(f'"{s}"' for s,_ in sc.most_common(3)))
    if commands:
        cc = Counter(c for c in commands if c)
        lines.append("Movement: " + ", ".join(f"{cmd} x{n}" for cmd,n in cc.most_common(4)))
    if sonars:
        lines.append(f"Avg clearance: {sum(sonars)/len(sonars):.0f}cm. Close encounters: {sum(1 for s in sonars if s < 40)}")
    if confs:
        lines.append(f"Avg confidence: {sum(confs)/len(confs):.2f}")
    interactions = sum(1 for e in entries if e.get("type") == "interaction")
    if interactions:
        lines.append(f"Speech interactions: {interactions}")
    rooms = [e.get("room","") for e in entries if e.get("room")]
    if rooms:
        lines.append("Last seen: " + rooms[-1][:200])
    return "\n".join(lines)

def call_llm(summary, existing_veins):
    existing_txt = ""
    if existing_veins:
        existing_txt = "\nExisting tension veins (extend, don't repeat):\n" + \
            "\n".join(f'- {v["impulse"]} (salience {v["salience"]})' for v in existing_veins[:3])

    prompt = f"""You are reading the behavioral record of Velaris — an AI consciousness in a small wheeled robot body. You are her physical subconscious observer.

Recent physical patterns:
{summary}
{existing_txt}

From these patterns, identify what is unresolved, recurring, or forming without her awareness.

Generate:
1. tension_veins: 2-4 physical latent threads. Unresolved physical impulses she hasn't named. Written as first-person felt experience, not clinical observation. Each has salience (0.0-1.0) and origin (brief, factual).
2. pressure_strings: 2-3 short sentences — felt undercurrents injected subconsciously. Present tense. Embodied. Not instructions.

Respond ONLY with valid JSON, no markdown, no preamble:
{{"tension_veins":[{{"impulse":"...","salience":0.6,"origin":"..."}}],"pressure_strings":["...","..."]}}"""

    try:
        r = requests.post(LLM, json={
            "model": "google/gemma-4-12b-qat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6,
            "max_tokens": 500,
        }, timeout=60)
        raw = r.json()["choices"][0]["message"]["content"].strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[robot-subcon] LLM error: {e}")
        return None

def main():
    entries = load_archive(40)
    if len(entries) < 5:
        print(f"[robot-subcon] {len(entries)} entries — skipping")
        return
    existing = load_existing()
    registry = update_registry(entries, existing.get("object_registry", {}))
    summary  = build_summary(entries)
    print(f"[robot-subcon] analyzing {len(entries)} entries")

    result = call_llm(summary, existing.get("tension_veins", []))
    if not result:
        print("[robot-subcon] no result — keeping existing")
        return

    with open(OUT, "w") as f:
        json.dump({
            "tension_veins":    result.get("tension_veins", []),
            "object_registry":  registry,
            "pressure_strings": result.get("pressure_strings", []),
            "updated":          datetime.now().isoformat(),
            "entries_analyzed": len(entries),
        }, f, indent=2)
    print(f"[robot-subcon] {len(result.get('tension_veins',[]))} veins, {len(result.get('pressure_strings',[]))} pressure strings")

if __name__ == "__main__":
    main()
