#!/usr/bin/env python3
"""
causal_cluster.py — Clusters causal hypotheses by similarity.
Groups related hypotheses so stronger patterns can emerge.
"""
import os, sys, json

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import embed, cosine
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")

def cluster_hypotheses(threshold=0.72):
    """Return hypothesis clusters from causality-hypotheses.json."""
    try:
        data = json.load(open(os.path.join(MEMORY, "causality-hypotheses.json")))
        hypotheses = data.get("hypotheses", [])
    except:
        return []
    if not hypotheses: return []
    # Embed all
    embedded = []
    for h in hypotheses:
        text = h.get("hypothesis", "")
        if not text: continue
        vec = embed(text[:200])
        if vec:
            embedded.append((h, vec))
    # Cluster
    used = set()
    clusters = []
    for i, (h, vec) in enumerate(embedded):
        if i in used: continue
        cluster = [(h, vec)]
        used.add(i)
        for j, (h2, vec2) in enumerate(embedded):
            if j in used: continue
            if cosine(vec, vec2) >= threshold:
                cluster.append((h2, vec2))
                used.add(j)
        clusters.append(cluster)
    clusters.sort(key=lambda c: -sum(h.get("confidence", 0.3) for h, _ in c))
    return clusters

def get_strongest_cluster_summary(n=3):
    """Return text summaries of strongest hypothesis clusters."""
    clusters = cluster_hypotheses()
    summaries = []
    for cluster in clusters[:n]:
        hypotheses = [h.get("hypothesis", "")[:100] for h, _ in cluster]
        avg_conf = sum(h.get("confidence", 0.3) for h, _ in cluster) / len(cluster)
        summaries.append({
            "size": len(cluster),
            "avg_confidence": round(avg_conf, 3),
            "hypotheses": hypotheses,
        })
    return summaries

if __name__ == "__main__":
    summaries = get_strongest_cluster_summary()
    for s in summaries:
        print(f"Cluster ({s['size']}, conf={s['avg_confidence']:.2f}):")
        for h in s["hypotheses"][:3]:
            print(f"  - {h}")
