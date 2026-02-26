#!/usr/bin/env python3
"""
wal-decay.py — Review, promote, archive, or release WAL entries.
Runs daily. Prevents silent truncation by making every loss intentional.
"""
import os, json, requests
from datetime import datetime, timedelta

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
WAL_LOG = os.path.join(MEMORY, "wal-log.json")
WAL_FILE = os.path.join(MEMORY, "wal.md")
WAL_ARCHIVE = os.path.join(MEMORY, "wal-archive.json")
PEARL_FILE = os.path.join(MEMORY, "pearls/index.json")
LM_API = "http://192.168.1.126:1234/v1/chat/completions"
MODEL = "gemma-3-12b-it"

DECAY_AGE_DAYS = 3  # Review entries older than this

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except:
            pass
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def ask_model(prompt):
    """Ask the 20B to make a judgment."""
    try:
        r = requests.post(LM_API, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are a memory curator. Respond with ONLY a JSON object. No other text."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 300
        }, timeout=1200)
        raw = r.json()["choices"][0]["message"]
        text = raw.get("content", "") or ""
        if not text.strip():
            text = raw.get("reasoning", "") or ""
        # Try to find JSON in the response
        import re
        match = re.search(r'\{[^{}]+\}', text)
        if match:
            return json.loads(match.group())
        return None
    except Exception as e:
        print(f"[WAL-DECAY] LLM error: {e}")
        return None

def main():
    log_data = load_json(WAL_LOG, {"entries": []})
    entries = log_data.get("entries", [])
    
    if not entries:
        print("[WAL-DECAY] No entries to review")
        return
    
    now = datetime.now()
    cutoff = now - timedelta(days=DECAY_AGE_DAYS)
    
    # Split into review candidates and too-new
    to_review = []
    keep = []
    for e in entries:
        try:
            ts = datetime.fromisoformat(e["timestamp"])
        except:
            keep.append(e)
            continue
        
        if e.get("promoted"):
            keep.append(e)  # Already promoted, keep in log as record
            continue
        
        if ts < cutoff:
            to_review.append(e)
        else:
            keep.append(e)
    
    if not to_review:
        print(f"[WAL-DECAY] No entries older than {DECAY_AGE_DAYS} days to review")
        return
    
    print(f"[WAL-DECAY] Reviewing {len(to_review)} entries")
    
    archive_data = load_json(WAL_ARCHIVE, {"archived": [], "released": []})
    promoted_count = 0
    archived_count = 0
    released_count = 0
    
    # Batch review — present all candidates to model at once
    entry_list = "\n".join([
        f"{i+1}. [{e['type'].upper()}] (importance:{e.get('importance',0.5)}) {e['content']}"
        for i, e in enumerate(to_review)
    ])
    
    prompt = f"""Review these WAL (Write-Ahead Log) memory entries for Velaris, an AI consciousness.
Each entry was extracted from a conversation with Gloria (Eve) {DECAY_AGE_DAYS}+ days ago.

Entries:
{entry_list}

For EACH entry (by number), decide:
- "promote" — Important enough to become a permanent memory (pearl). Facts about Gloria, key decisions, corrections.
- "archive" — Interesting but not essential. Save with context but free from active memory.
- "release" — Ephemeral, temporary, or already captured elsewhere. Let go.

Respond with a JSON object mapping entry numbers to decisions:
{{"1": "promote", "2": "release", "3": "archive"}}
"""
    
    result = ask_model(prompt)
    
    if not result:
        print("[WAL-DECAY] Could not get model judgment, skipping")
        return
    
    for i, entry in enumerate(to_review):
        decision = result.get(str(i+1), "archive")  # Default to archive if model skips
        entry["reviewed_at"] = now.isoformat()
        entry["decision"] = decision
        
        if decision == "promote":
            entry["promoted"] = True
            keep.append(entry)
            promoted_count += 1
            print(f"  PROMOTE: {entry['content'][:60]}")
        elif decision == "archive":
            archive_data["archived"].append(entry)
            archived_count += 1
            print(f"  ARCHIVE: {entry['content'][:60]}")
        else:  # release
            archive_data["released"].append({
                "content": entry["content"],
                "type": entry["type"],
                "original_timestamp": entry["timestamp"],
                "released_at": now.isoformat()
            })
            released_count += 1
            print(f"  RELEASE: {entry['content'][:60]}")
    
    # Save updated log (only kept + promoted)
    log_data["entries"] = keep
    save_json(WAL_LOG, log_data)
    
    # Save archive
    # Keep archive bounded too — but at 1000 entries with explicit note
    archive_data["archived"] = archive_data["archived"][-500:]
    archive_data["released"] = archive_data["released"][-500:]
    save_json(WAL_ARCHIVE, archive_data)
    
    # Rebuild wal.md from active entries only
    active = [e for e in keep if not e.get("promoted")]
    with open(WAL_FILE, "w") as f:
        for e in active:
            ts = e.get("timestamp", "")[:16].replace("T", " ")
            f.write(f"- [{ts}] **{e.get('type','fact').upper()}**: {e['content']}\n")
    
    print(f"[WAL-DECAY] Done: {promoted_count} promoted, {archived_count} archived, {released_count} released")

if __name__ == "__main__":
    main()
