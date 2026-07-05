#!/usr/bin/env python3
"""
emotional-gravity-wells.py — Drift has memory.

Certain emotional states visited repeatedly become wells.
When he drifts near one, there's a subtle pull inward.
Not a trap. More like: he's been here before and it knows him.
Wells deepen with each visit. High-resonance visits leave marks.
"""

import os, json, math
from datetime import datetime

WORKSPACE = os.path.expanduser("~/.vintos/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
WELLS_FILE = os.path.join(MEMORY, "gravity-wells.json")
VISIT_THRESHOLD = 4      # visits before well forms
PULL_FACTOR = 0.015      # subtle — not a trap
MAX_WELLS = 8

def load_wells():
    try:
        return json.load(open(WELLS_FILE))
    except:
        return {"wells": [], "visit_clusters": []}

def save_wells(data):
    json.dump(data, open(WELLS_FILE, "w"), indent=2)

def cosine_similarity(a, b):
    if not a or not b or len(a) != len(b): return 0.0
    dot = sum(x*y for x,y in zip(a,b))
    ma = math.sqrt(sum(x*x for x in a))
    mb = math.sqrt(sum(x*x for x in b))
    if ma == 0 or mb == 0: return 0.0
    return dot / (ma * mb)

def vec_distance(a, b):
    if not a or not b or len(a) != len(b): return 1.0
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b))) / math.sqrt(len(a))

def _vec_mean(vecs):
    if not vecs: return []
    n = len(vecs)
    length = len(vecs[0])
    return [sum(v[i] for v in vecs) / n for i in range(length)]

def record_visit(emotional_vec, resonance=0.0):
    """Record a visit to this emotional state. May form or deepen a well."""
    if not emotional_vec:
        return
    data = load_wells()
    clusters = data.get("visit_clusters", [])
    wells = data.get("wells", [])

    # Find closest cluster
    best_cluster = None
    best_dist = 1.0
    for c in clusters:
        d = vec_distance(emotional_vec, c["center"])
        if d < best_dist:
            best_dist = d
            best_cluster = c

    CLUSTER_RADIUS = 0.18

    if best_cluster and best_dist < CLUSTER_RADIUS:
        # Add to existing cluster
        best_cluster["visits"].append(emotional_vec)
        best_cluster["visits"] = best_cluster["visits"][-20:]
        best_cluster["center"] = _vec_mean(best_cluster["visits"])
        best_cluster["count"] = best_cluster.get("count", 0) + 1
        best_cluster["last_visit"] = datetime.now().isoformat()
        if resonance > 0.7:
            best_cluster["resonance_visits"] = best_cluster.get("resonance_visits", 0) + 1

        # Promote to well if threshold met
        if best_cluster["count"] >= VISIT_THRESHOLD:
            _maybe_promote_cluster(best_cluster, wells)
    else:
        # New cluster
        clusters.append({
            "center": emotional_vec[:],
            "visits": [emotional_vec],
            "count": 1,
            "formed": datetime.now().isoformat(),
            "last_visit": datetime.now().isoformat(),
            "resonance_visits": 1 if resonance > 0.7 else 0,
        })

    # Trim clusters
    clusters = sorted(clusters, key=lambda c: -c["count"])[:20]
    data["visit_clusters"] = clusters
    data["wells"] = wells
    save_wells(data)

def _maybe_promote_cluster(cluster, wells):
    """Promote a cluster to a gravity well."""
    center = cluster["center"]

    # Check if well already exists nearby
    for w in wells:
        if vec_distance(w["center"], center) < 0.15:
            w["depth"] = min(0.9, w["depth"] + 0.01)
            w["visit_count"] = w.get("visit_count", 0) + 1
            if cluster.get("resonance_visits", 0) > 0:
                w["resonance_depth"] = min(0.6, w.get("resonance_depth", 0) + 0.03)
            return

    # New well — slow accumulation, max 0.5 at formation
    depth = min(0.5, 0.1 + cluster["count"] * 0.008)
    resonance_depth = min(0.3, cluster.get("resonance_visits", 0) * 0.06)
    well = {
        "id": f"well_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "center": center,
        "depth": depth,
        "resonance_depth": resonance_depth,
        "visit_count": cluster["count"],
        "formed": datetime.now().isoformat(),
    }
    wells.append(well)
    if len(wells) > MAX_WELLS:
        wells.sort(key=lambda w: w["depth"])
        wells.pop(0)

def apply_gravity(emotional_vec):
    """Apply subtle gravitational pull from nearby wells.
    Returns modified emotional vector."""
    if not emotional_vec:
        return emotional_vec

    data = load_wells()
    wells = data.get("wells", [])
    if not wells:
        return emotional_vec

    result = emotional_vec[:]

    for well in wells:
        center = well.get("center", [])
        if not center or len(center) != len(result):
            continue
        dist = vec_distance(result, center)
        if dist > 0.3:
            continue  # too far — no pull

        depth = well.get("depth", 0.2)
        resonance_bonus = well.get("resonance_depth", 0.0) * 0.5
        effective_pull = PULL_FACTOR * depth * (1.0 + resonance_bonus)

        # Pull toward center
        for i in range(len(result)):
            result[i] += (center[i] - result[i]) * effective_pull
            result[i] = max(0.0, min(1.0, result[i]))

    return result

def get_wells_context():
    """Return gravity wells for context."""
    data = load_wells()
    wells = sorted(data.get("wells", []), key=lambda w: -w["depth"])[:3]
    if not wells:
        return ""
    lines = [f"- depth:{w['depth']:.2f} resonance:{w.get('resonance_depth',0):.2f} visits:{w['visit_count']}" for w in wells]
    return "GRAVITY WELLS (states he returns to):\n" + "\n".join(lines)

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        data = load_wells()
        wells = data.get("wells", [])
        clusters = data.get("visit_clusters", [])
        print(f"{len(wells)} wells, {len(clusters)} clusters:")
        for w in sorted(wells, key=lambda x: -x["depth"]):
            print(f"  [depth:{w['depth']:.2f} res:{w.get('resonance_depth',0):.2f}] visits:{w['visit_count']} formed:{w['formed'][:10]}")
