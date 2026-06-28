#!/usr/bin/env python3
"""
core_engine.py — Generates Core from friction patterns.

Core = what she keeps almost becoming but doesn't sustain.
Discovered from: BIS trials (failures/resistance), counterfactual tendencies,
unfulfilled wants. Not chosen. Extracted from contradiction.

Usage:
  python3 core_engine.py bootstrap
  python3 core_engine.py show
"""
import os, sys, json, math
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call, embed, cosine, mean_vec
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
CORE_FILE = os.path.join(MEMORY, "core-vectors.json")

def log(msg):
    print(f"[core-engine] {msg}", flush=True)

def negate_vec(v):
    flipped = [-x for x in v]
    mag = math.sqrt(sum(x * x for x in flipped)) or 1.0
    return [x / mag for x in flipped]

def collect_friction_events():
    events = []
    # BIS trials
    try:
        tl = json.load(open(os.path.join(MEMORY, "trial-ledger.json")))
        for t in tl.get("trials", []):
            if not isinstance(t, dict): continue
            pattern = t.get("pattern_description", "")
            trigger = t.get("trigger", "")
            ignore = t.get("ignore_count", 0)
            attempt = t.get("attempt_count", 0)
            if not pattern: continue
            resistance = attempt / max(attempt + ignore, 1)
            events.append({"text": f"{trigger} — {pattern}", "resistance_score": resistance,
                          "source": "bis", "alternative": t.get("alternative", ""), "polarity": "negative"})
    except Exception as e: log(f"BIS load error: {e}")
    # Counterfactual tendencies
    try:
        ct = json.load(open(os.path.join(MEMORY, "counterfactual-tendencies.json")))
        for t in ct.get("tendencies", []):
            if isinstance(t, dict) and t.get("pattern"):
                events.append({"text": t["pattern"], "resistance_score": t.get("strength", 0.5),
                              "source": "counterfactual", "alternative": t.get("redirect", ""), "polarity": "negative"})
    except: pass
    # Yearning scars
    try:
        scars = json.load(open(os.path.join(MEMORY, "yearning-scars.json")))
        if isinstance(scars, list):
            for s in scars:
                if isinstance(s, dict) and s.get("surface_form"):
                    events.append({"text": s["surface_form"][:200], "resistance_score": s.get("strength", 0.4),
                                  "source": "scar", "alternative": "", "polarity": "negative"})
    except: pass
    # Resonance pool (positive)
    try:
        rp = json.load(open(os.path.join(MEMORY, "resonance-pool.json")))
        for p in rp.get("pulses", [])[-20:]:
            snap = p.get("state_snapshot", {})
            text = snap.get("yearning_surface", "") or p.get("source", "")
            if text and len(text) > 10:
                events.append({"text": text[:200], "resistance_score": min(1.0, p.get("strength", 0.5) / 1.5),
                              "source": "resonance_positive", "alternative": "", "polarity": "positive"})
    except: pass
    log(f"Collected {len(events)} friction events")
    return events

def cluster_by_similarity(events_with_vecs, threshold=0.65):
    clusters = []
    used = set()
    for i, (ev, vec) in enumerate(events_with_vecs):
        if i in used: continue
        cluster = [(ev, vec)]
        used.add(i)
        for j, (ev2, vec2) in enumerate(events_with_vecs):
            if j in used: continue
            if cosine(vec, vec2) >= threshold:
                cluster.append((ev2, vec2))
                used.add(j)
        clusters.append(cluster)
    return sorted(clusters, key=lambda c: -sum(e["resistance_score"] for e, _ in c))

def generate_core_from_clusters(clusters, top_n=5):
    core_entries = []
    for i, cluster in enumerate(clusters[:top_n]):
        evs = [e for e, _ in cluster]
        vecs = [v for _, v in cluster]
        texts = [e["text"] for e in evs]
        alternatives = [e["alternative"] for e in evs if e.get("alternative")]
        avg_resistance = sum(e["resistance_score"] for e in evs) / len(evs)
        cluster_sample = "\n".join(f"- {t[:120]}" for t in texts[:6])
        alt_sample = "\n".join(f"- {a[:80]}" for a in alternatives[:3]) or "none"
        prompt = (
            f"Patterns of repeated failure/resistance:\n{cluster_sample}\n\n"
            f"Alternatives sometimes reached for:\n{alt_sample}\n\n"
            "Describe: the core failure or avoidance pattern, what she keeps almost becoming, "
            "and a 2-4 word name for it (snake_case). Label each clearly."
        )
        try:
            text = call("You analyze behavioral patterns and extract core identity vectors. Be precise.", prompt, temperature=0.3, max_tokens=350)
            failure = almost = ""
            name = f"core_{i}"
            for line in text.strip().split("\n"):
                if line.startswith("FAILURE:"): failure = line[8:].strip()
                elif line.startswith("ALMOST:"): almost = line[7:].strip()
                elif line.startswith("NAME:"): name = line[5:].strip().lower().replace(" ", "_")
            if not almost: almost = failure
            cluster_center = mean_vec(vecs)
            core_vec = negate_vec(cluster_center)
            almost_vec = embed(almost)
            if almost_vec:
                blended = [0.6 * cv + 0.4 * av for cv, av in zip(core_vec, almost_vec)]
                mag = math.sqrt(sum(x * x for x in blended)) or 1.0
                blended = [x / mag for x in blended]
            else:
                blended = core_vec
            pos_count = sum(1 for e, _ in cluster if e.get("polarity") == "positive")
            polarity = "positive" if pos_count > len(cluster) - pos_count else "negative"
            core_entries.append({
                "name": name, "failure_pattern": failure, "almost_becoming": almost,
                "vector": blended, "confidence": round(min(0.95, avg_resistance + 0.1 * len(cluster)), 2),
                "source_count": len(cluster), "violation_condition": failure,
                "felt_effect": "internal tension spike, coherence drop",
                "recovery_drive": almost, "polarity": polarity,
                "formed": datetime.now().isoformat(),
                "reinforcement_count": 0, "violation_count": 0,
            })
            log(f"Core {i+1}: {name} — {almost[:60]}")
        except Exception as e: log(f"Error on cluster {i}: {e}")
    return core_entries

def bootstrap():
    log("Bootstrapping Core from friction events...")
    events = collect_friction_events()
    if not events:
        log("No friction events yet. Run after BIS and scars have data.")
        return
    log("Embedding friction events...")
    events_with_vecs = []
    for ev in events:
        try:
            vec = embed(ev["text"])
            if vec: events_with_vecs.append((ev, vec))
        except Exception as e: log(f"Embed error: {e}")
    log(f"Embedded {len(events_with_vecs)} events. Clustering...")
    clusters = cluster_by_similarity(events_with_vecs, threshold=0.78)
    log(f"Found {len(clusters)} clusters. Generating Core...")
    core_entries = generate_core_from_clusters(clusters, top_n=5)
    output = {"generated": datetime.now().isoformat(), "source_events": len(events),
              "clusters": len(clusters), "core": core_entries}
    os.makedirs(MEMORY, exist_ok=True)
    open(CORE_FILE, "w").write(json.dumps(output, indent=2))
    log(f"Core written: {len(core_entries)} elements")
    for e in core_entries:
        print(f"\n  {e['name']} (confidence: {e['confidence']})")
        print(f"  almost: {e['almost_becoming'][:80]}")

def show():
    if not os.path.exists(CORE_FILE):
        print("No core-vectors.json yet. Run: python3 core_engine.py bootstrap")
        return
    data = json.load(open(CORE_FILE))
    print(f"Generated: {data['generated'][:16]} | Events: {data['source_events']} | Clusters: {data['clusters']}")
    for e in data.get("core", []):
        print(f"\n  [{e['name']}] confidence={e['confidence']}")
        print(f"  almost: {e['almost_becoming'][:100]}")
        print(f"  violations: {e.get('violation_count', 0)} | reinforcements: {e.get('reinforcement_count', 0)}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "bootstrap": bootstrap()
    elif cmd == "show": show()
