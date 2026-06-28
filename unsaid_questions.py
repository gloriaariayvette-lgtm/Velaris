#!/usr/bin/env python3
"""
unsaid_questions.py — Questions Vintos wants to ask Gloria but hasn't.
Accumulated. Sometimes delivered. Sometimes just held.
"""
import os, sys, json, uuid
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from model_utils import call_utility
MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
QUESTIONS_FILE = os.path.join(MEMORY, "unsaid-questions.json")

def load():
    try: return json.load(open(QUESTIONS_FILE))
    except: return {"questions": []}

def save(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(QUESTIONS_FILE, "w"), indent=2)

def add_question(text, urgency=0.5, source=""):
    data = load()
    data.setdefault("questions", []).append({
        "id": f"q-{uuid.uuid4().hex[:5]}",
        "text": text[:300],
        "urgency": round(urgency, 3),
        "source": source,
        "formed": datetime.now().isoformat(),
        "asked": False,
    })
    data["questions"] = [q for q in data["questions"] if not q.get("asked")][-60:]
    save(data)

def detect_from_exchange(gloria_text, vintos_response, source="exchange"):
    """Did this exchange generate a question Vintos didn't ask?"""
    prompt = (
        f"Gloria: {gloria_text[:300]}\n"
        f"Vintos replied: {vintos_response[:300]}\n\n"
        "Is there something Vintos wanted to ask but didn't? "
        "Not rhetorical. A real question she has about Gloria or their dynamic.\n"
        "Output: YES|question text (max 80 chars)|urgency (0.0-1.0)\n"
        "Or: NO"
    )
    try:
        result = call_utility("Detect unsaid question.", prompt, temperature=0.2, max_tokens=60)
        if result.strip().upper().startswith("NO"): return None
        parts = result.strip().split("|")
        if len(parts) >= 3:
            question = parts[1].strip()
            try: urgency = float(parts[2].strip())
            except: urgency = 0.4
            if question:
                add_question(question, urgency=urgency, source=source)
                return question
    except: pass
    return None

def mark_asked(question_id):
    data = load()
    for q in data.get("questions", []):
        if q.get("id") == question_id:
            q["asked"] = True
            q["asked_at"] = datetime.now().isoformat()
            break
    save(data)

def get_top_unsaid(n=3):
    data = load()
    pending = [q for q in data.get("questions", []) if not q.get("asked")]
    pending.sort(key=lambda q: -q.get("urgency", 0))
    return pending[:n]

def get_questions_context():
    pending = get_top_unsaid(3)
    if not pending: return ""
    lines = ["[questions not yet asked]"]
    for q in pending:
        lines.append(f"  {q['text'][:80]}")
    return "\n".join(lines)

if __name__ == "__main__":
    print(get_questions_context())
