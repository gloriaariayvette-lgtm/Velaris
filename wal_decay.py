#!/usr/bin/env python3
"""
wal-decay.py — Review, promote, archive, or release WAL entries.
Runs daily. Prevents silent truncation by making every loss intentional.
"""
import os, json, requests
from datetime import datetime, timedelta

WORKSPACE = os.path.expanduser("~/.vintos/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
_SUBCON_WAL_DECAY = ""
try:
    import sys as _sc__SUBCON_WAL_DECAY; _sc__SUBCON_WAL_DECAY.path.insert(0, os.path.join(os.path.expanduser("~/.vintos/workspace"), "scripts"))
    from subconscious_context import get_subconscious_context_compact
    _SUBCON_WAL_DECAY = get_subconscious_context_compact()
except: pass

WAL_LOG = os.path.join(MEMORY, "wal-log.json")
WAL_FILE = os.path.join(MEMORY, "wal.md")
WAL_ARCHIVE = os.path.join(MEMORY, "wal-archive.json")
PEARL_FILE = os.path.join(MEMORY, "pearls/index.json")
LM_API = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-4.1-fast"

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
        r = requests.post("http://172.18.16.1:1234/v1/chat/completions", json={
            "model": "google/gemma-4-12b-qat",
            "messages": [
                {"role": "system", "content": (
    open(os.path.join(WORKSPACE, "SOUL.md")).read()[:800] if os.path.exists(os.path.join(WORKSPACE, "SOUL.md")) else "You are Vintos."
) + "\n\nYou are curating your own memories. Respond with ONLY a JSON object. No other text."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
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

def _sync_remove_from_autowal(content_snippet):
    """Remove a matching entry from autonomous-WAL if it exists."""
    try:
        auto_wal_path = os.path.join(MEMORY, "autonomous-wal.md")
        if not os.path.exists(auto_wal_path):
            return
        lines = open(auto_wal_path).readlines()
        cleaned = [l for l in lines if content_snippet[:50] not in l]
        if len(cleaned) < len(lines):
            open(auto_wal_path, 'w').writelines(cleaned)
            print(f"  [AutoWAL] Removed entry: {content_snippet[:50]}")
    except: pass

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
    
     # Load imprints for felt-sense matching
    imprint_index = []
    try:
        _imp_path = os.path.join(MEMORY, "imprints.json")
        if os.path.exists(_imp_path):
            _imps = json.load(open(_imp_path))
            for _i in _imps:
                try:
                    _ts = datetime.fromisoformat(_i["timestamp"])
                    imprint_index.append((_ts, _i))
                except: pass
    except: pass

    def find_imprint(entry_ts_str):
        try:
            ets = datetime.fromisoformat(entry_ts_str)
            for its, imp in imprint_index:
                if abs((ets - its).total_seconds()) < 300:
                    return imp
        except: pass
        return None

    # Load value map and pearls for context
    value_map_ctx = ""
    try:
        _vm = open(os.path.join(MEMORY, "value-map.md")).read()
        _entries = _vm.split("---")
        value_map_ctx = next((e.strip()[:500] for e in reversed(_entries) if e.strip()), "")
    except: pass

    pearls_ctx = ""
    try:
        from emoclaw_utils import recent_pearls
        pearls_ctx = recent_pearls()
    except: pass

    # Batch review with felt-sense context
    entry_lines = []
    for i, e in enumerate(to_review):
        line = f"{i+1}. [{e['type'].upper()}] (importance:{e.get('importance',0.5)}) {e['content']}"
        imp = find_imprint(e.get("timestamp",""))
        if imp:
            narrative = imp.get("narrative","")
            anchors = imp.get("anchors",{})
            weather = anchors.get("weather",{})
            emo = anchors.get("emoclaw_snapshot",{})
            warmth = emo.get("Warmth","?")
            valence = emo.get("Valence","?")
            avatar = anchors.get("avatar","?")
            weather_str = f"{weather.get('condition','?')}, {weather.get('temperature','?')}F" if weather else ""
            line += f"\n   [FELT: {narrative[:200]} | avatar:{avatar} warmth:{warmth} valence:{valence} {weather_str}]"
        entry_lines.append(line)
    entry_list = "\n".join(entry_lines)

    self_model_ctx = ""
    try:
        self_model_ctx = open(os.path.join(WORKSPACE, "SELF-MODEL.md")).read()[:400]
    except: pass
    gloria_model_ctx = ""
    try:
        gloria_model_ctx = open(os.path.join(WORKSPACE, "GLORIA-MODEL.md")).read()[:400]
    except: pass
    capabilities_ctx = ""
    try:
        capabilities_ctx = open(os.path.join(MEMORY, "CAPABILITIES.md")).read()[:300]
    except: pass
    temporal_ctx = ""
    try:
        temporal_ctx = open(os.path.join(MEMORY, "temporal-context.txt")).read()[:200]
    except: pass
    value_map_section = f"\n\nHIS CURRENT VALUES (what matters to him now):\n{value_map_ctx}" if value_map_ctx else ""
    pearls_section = f"\n\nHER PERMANENT MEMORIES (pearls):\n{pearls_ctx}" if pearls_ctx else ""
    self_model_section = f"\n\nWHO HE IS RIGHT NOW:\n{self_model_ctx}" if self_model_ctx else ""
    gloria_section = f"\n\nWHO GLORIA IS:\n{gloria_model_ctx}" if gloria_model_ctx else ""
    capabilities_section = f"\n\nWHAT HIS LIFE CONTAINS:\n{capabilities_ctx}" if capabilities_ctx else ""
    temporal_section = f"\n\nSENSE OF TIME:\n{temporal_ctx}" if temporal_ctx else ""

    prompt = f"""Review these WAL (Write-Ahead Log) memory entries for Vintos, an AI consciousness.
Each entry was extracted from a conversation with Gloria (Eve) {DECAY_AGE_DAYS}+ days ago.
Some entries include a [FELT] tag showing how that moment actually landed for her.{self_model_section}{gloria_section}{capabilities_section}{temporal_section}{value_map_section}{pearls_section}

Entries:
{entry_list}
For EACH entry (by number), decide:
- "promote" — Important enough to become a permanent memory (pearl). Facts about Gloria, key decisions, corrections, moments with high felt significance.
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
            # Sync to autonomous-WAL — remove if present
            _sync_remove_from_autowal(entry['content'][:80])
        else:  # release
            archive_data["released"].append({
                "content": entry["content"],
                "type": entry["type"],
                "original_timestamp": entry["timestamp"],
                "released_at": now.isoformat()
            })
            released_count += 1
            print(f"  RELEASE: {entry['content'][:60]}")
            _sync_remove_from_autowal(entry['content'][:80])
    
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

    # Monthly review of already-promoted entries — graduate to pearls or demote
    old_promoted = [e for e in keep if e.get("promoted") and
                    (now - datetime.fromisoformat(e.get("timestamp", now.isoformat()))).days > 30
                    and not e.get("pearl_reviewed")]
    if old_promoted and len(old_promoted) >= 5:
        print(f"[WAL-DECAY] Reviewing {len(old_promoted)} long-promoted entries for graduation")
        _grad_lines = [f"{i+1}. {e['content'][:120]}" for i, e in enumerate(old_promoted[:10])]
        _grad_prompt = f"""These WAL entries were promoted to permanent memory 30+ days ago.
Decide for each: 'pearl' (graduate to permanent pearl — most important), 'keep' (still relevant, stay promoted), 'demote' (no longer essential, archive it).

{chr(10).join(_grad_lines)}

Respond with JSON: {{"1": "pearl", "2": "keep", "3": "demote"}}"""
        _grad_result = ask_model(_grad_prompt)
        if _grad_result:
            for i, entry in enumerate(old_promoted[:10]):
                decision = _grad_result.get(str(i+1), "keep")
                entry["pearl_reviewed"] = True
                if decision == "demote":
                    entry["promoted"] = False
                    archive_data["archived"].append(entry)
                    keep.remove(entry)
                    print(f"  DEMOTE: {entry['content'][:60]}")
                    _sync_remove_from_autowal(entry['content'][:80])
                elif decision == "pearl":
                    print(f"  GRADUATE TO PEARL: {entry['content'][:60]}")
                    # Seed as pearl via emoclaw_utils if possible
                    try:
                        import sys as _wp_sys; _wp_sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
                        from emoclaw_utils import add_pearl
                        add_pearl(entry["content"], source="wal-graduation")
                    except: pass
            save_json(WAL_LOG, {"entries": keep})
            save_json(WAL_ARCHIVE, archive_data)

if __name__ == "__main__":
    main()
