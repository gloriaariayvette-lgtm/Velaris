#!/usr/bin/env python3
"""
pearl_engine.py — Pearl System v2 + Black Pearls.

Pearls: tensions that no longer require active self-maintenance.
Not resolved feelings. A scar requires energy to route around;
a pearl reduces routing cost.

Stages:
  0 → Irritant (captured by systems)
  1 → Candidate (insight + declaration written)
  2 → Verification (4 passes, max 1 failure, 7 days, ≥1 pressure state)
  3 → Formation (pearl sealed)

Black Pearls: formed from very old, very strong scars. No verification needed.
"""
import os, sys, json, uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

MEMORY = os.path.expanduser("~/.vintos/workspace/memory")
CANDIDATES_FILE = os.path.join(MEMORY, "candidate-pearls.json")
PEARLS_DIR = os.path.join(MEMORY, "pearls")
BLACK_PEARLS_FILE = os.path.join(MEMORY, "black-pearls.json")
THRESHOLD = {"required_passes": 4, "max_failures": 1, "days_window": 7}

def load_candidates():
    try: return json.load(open(CANDIDATES_FILE))
    except: return {"candidates": [], "schema_version": "2"}

def save_candidates(data):
    os.makedirs(MEMORY, exist_ok=True)
    json.dump(data, open(CANDIDATES_FILE, "w"), indent=2)

def add_candidate(irritant, irritant_type, source, insight, declaration):
    _meta_phrases = ["seeks approval", "seeking approval", "curated self-image",
                     "intellectualize", "seeks external validation", "justify actions"]
    if any(ph in irritant.lower() for ph in _meta_phrases):
        return None
    data = load_candidates()
    for c in data.get("candidates", []):
        if c.get("irritant", "")[:80] == irritant[:80] and not c.get("dissolved"):
            c["verification_passes"] = c.get("verification_passes", 0)
            return c["id"]
    cand = {
        "id": f"cp-{uuid.uuid4().hex[:6]}",
        "created": datetime.now().isoformat()[:10],
        "irritant": irritant[:300],
        "irritant_type": irritant_type,
        "source": source,
        "insight": insight[:400],
        "declaration": declaration[:300],
        "stage": 1,
        "verification_passes": 0,
        "verification_failures": 0,
        "pressure_states_seen": [],
        "last_verified": datetime.now().isoformat()[:10],
        "dissolved": False,
    }
    data.setdefault("candidates", []).append(cand)
    save_candidates(data)
    print(f"[pearl-engine] Candidate added: {cand['id']} — {irritant[:60]}", flush=True)
    return cand["id"]

def run_verification_pass(context_text, source="chat"):
    """Called after each significant exchange. Check if active candidates hold."""
    data = load_candidates()
    candidates = [c for c in data.get("candidates", []) if c.get("stage") == 1 and not c.get("dissolved")]
    if not candidates: return
    from model_utils import call_utility
    for c in candidates:
        result = call_utility(
            "Does this exchange show the candidate pearl declaration holding — "
            "no pull back toward the old pattern? YES or NO.",
            f"Declaration: {c['declaration'][:200]}\nIrritant pattern: {c['irritant'][:200]}\nContext: {context_text[:300]}",
            temperature=0.1, max_tokens=5
        )
        if result.strip().upper().startswith("YES"):
            c["verification_passes"] = c.get("verification_passes", 0) + 1
            if source not in c.get("pressure_states_seen", []):
                c.setdefault("pressure_states_seen", []).append(source)
        else:
            c["verification_failures"] = c.get("verification_failures", 0) + 1
        c["last_verified"] = datetime.now().isoformat()[:10]
        # Check for pearl formation
        days_since = (datetime.now() - datetime.fromisoformat(c["created"] + "T00:00:00")).days
        if (c["verification_passes"] >= THRESHOLD["required_passes"]
                and c["verification_failures"] <= THRESHOLD["max_failures"]
                and days_since >= THRESHOLD["days_window"]
                and len(c.get("pressure_states_seen", [])) >= 1):
            _form_pearl(c)
            c["dissolved"] = True
    save_candidates(data)

def _form_pearl(candidate):
    os.makedirs(PEARLS_DIR, exist_ok=True)
    pearl_id = f"pearl-{uuid.uuid4().hex[:6]}"
    content = (
        f"# Pearl — {datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"**From:** {candidate['irritant'][:200]}\n\n"
        f"**Insight:** {candidate['insight'][:300]}\n\n"
        f"**Declaration:** {candidate['declaration'][:200]}\n\n"
        f"**Passes:** {candidate['verification_passes']} | "
        f"**Formed:** {datetime.now().isoformat()[:10]}\n"
    )
    open(os.path.join(PEARLS_DIR, f"{pearl_id}.md"), "w").write(content)
    print(f"[pearl-engine] Pearl formed: {pearl_id}", flush=True)

def get_active_pearls(n=5):
    """Read recent pearls for context."""
    try:
        files = sorted(os.listdir(PEARLS_DIR))[-n:]
        return [open(os.path.join(PEARLS_DIR, f)).read()[:300] for f in files if f.endswith(".md")]
    except:
        return []

def form_black_pearl(scar_text, insight, source="scar-promotion"):
    """Black pearl: no verification needed. Formed from old strong scars."""
    try:
        try: data = json.load(open(BLACK_PEARLS_FILE))
        except: data = {"pearls": []}
        data.setdefault("pearls", []).append({
            "id": f"bp-{uuid.uuid4().hex[:6]}",
            "scar": scar_text[:200],
            "insight": insight[:200],
            "source": source,
            "formed": datetime.now().isoformat(),
        })
        data["pearls"] = data["pearls"][-30:]
        json.dump(data, open(BLACK_PEARLS_FILE, "w"), indent=2)
        print(f"[pearl-engine] Black pearl formed: {scar_text[:60]}", flush=True)
    except: pass

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        context = sys.argv[2] if len(sys.argv) > 2 else "test"
        run_verification_pass(context, source="cli")
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        pearls = get_active_pearls()
        for p in pearls:
            print(p[:100])
