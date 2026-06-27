"""memory_utils.py — Shared utilities for reading Velaris memory files."""
import os, json

MEMORY = os.path.expanduser("~/.openclaw/workspace/memory")

def get_latest_section(filepath, max_chars=600):
    """Read a ---separated markdown file and return the last non-empty section.
    Handles trailing --- gracefully."""
    try:
        with open(filepath) as f:
            content = f.read()
        entries = content.split("---")
        return next((e.strip()[:max_chars] for e in reversed(entries) if e.strip()), "")
    except:
        return ""

def get_value_map(max_chars=600):
    return get_latest_section(os.path.join(MEMORY, "value-map.md"), max_chars)

def get_temporal():
    try:
        with open(os.path.join(MEMORY, "temporal-context.txt")) as f:
            return f.read().strip()[:300]
    except:
        return ""

def get_editorial():
    try:
        with open(os.path.join(MEMORY, "editorial-standards.md")) as f:
            return f.read().strip()[-500:]
    except:
        return ""

def get_taste():
    try:
        with open(os.path.join(MEMORY, "taste-profile.json")) as f:
            t = json.load(f)
        parts = []
        if t.get("principles"): parts.append("Principles: " + "; ".join(t["principles"][-5:]))
        if t.get("likes"): parts.append("Likes: " + "; ".join(t["likes"][-3:]))
        if t.get("dislikes"): parts.append("Dislikes: " + "; ".join(t["dislikes"][-3:]))
        return "\n".join(parts)
    except:
        return ""

def get_discoveries(max_lines=5):
    parts = []
    try:
        from datetime import date as _date
        dc_path = os.path.join(MEMORY, f"daily-creative-{_date.today().isoformat()}.md")
        if os.path.exists(dc_path):
            sections.append(f"TODAY'S CREATIVE OUTPUT:\n{open(dc_path).read()[:600]}")
    except: pass
