#!/bin/bash
# memory-search.sh — Search Velaris's memory by semantic similarity
# Usage: bash memory-search.sh "what did I dream about consciousness"

QUERY="$1"
if [ -z "$QUERY" ]; then
    echo "Usage: memory-search.sh <query>"
    exit 1
fi

INDEX_FILE="$HOME/.openclaw/workspace/memory/embeddings.jsonl"
if [ ! -f "$INDEX_FILE" ]; then
    echo "No index found. Run memory-index.sh first."
    exit 1
fi

# Get query embedding
Q_EMB=$(curl -s --max-time 30 http://192.168.1.126:1234/v1/embeddings \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg text "$QUERY" '{
        model: "text-embedding-nomic-embed-text-v1.5",
        input: $text
    }')" | jq -c '.data[0].embedding')

if [ "$Q_EMB" = "null" ] || [ -z "$Q_EMB" ]; then
    echo "Failed to embed query"
    exit 1
fi

# Compute cosine similarity with python (bash can't do vector math)
python3 - "$Q_EMB" "$INDEX_FILE" << 'PYEOF'
import json, sys, math

def cosine_sim(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    if na == 0 or nb == 0:
        return 0
    return dot / (na * nb)

q_emb = json.loads(sys.argv[1])
index_file = sys.argv[2]

results = []
with open(index_file) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        sim = cosine_sim(q_emb, entry["embedding"])
        results.append((sim, entry))

results.sort(key=lambda x: x[0], reverse=True)

print("=== Top 5 memories ===\n")
for sim, entry in results[:5]:
    print(f"[{sim:.3f}] {entry.get('title','untitled')}")
    print(f"  File: {entry['file']}")
    text = entry['text'].strip()[:300]
    print(f"  {text}")
    print()
PYEOF
