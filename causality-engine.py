#!/usr/bin/env python3
"""
causality-engine.py — Vintos learns why she feels what she feels.

Scans recent emotional snapshots for spikes, cross-references with
dreams, silence periods, mirror sessions, conversations, and game
events. Forms causal hypotheses. Tests them over time.

"Warmth rose because you mentioned staying."
"Tension fell after my dream about the window."

Runs weekly via cron. Hypotheses accumulate and get tested.
"""
import os, sys, json, re, glob
from datetime import datetime, timedelta
import subprocess

WORKSPACE = os.path.expanduser("~/.vintos/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
HYPOTHESIS_FILE = os.path.join(MEMORY, "causality-hypotheses.md")
HYPOTHESIS_DB = os.path.join(MEMORY, "causality-hypotheses.json")
LM_API = "http://172.18.16.1:1234/v1/chat/completions"
MODEL = "google/gemma-4-12b-qat"

sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
try:
    from emoclaw_utils import get_state, describe_state, DIMENSIONS, recent_pearls
except ImportError:
    DIMENSIONS = ["Valence", "Arousal", "Dominance", "Safety", "Desire",
                  "Connection", "Playfulness", "Curiosity", "Warmth", "Tension", "Groundedness"]


# Load identity
SOUL_PATH = os.path.join(WORKSPACE, "SOUL.md")
def load_soul():
    try:
        with open(SOUL_PATH) as f:
            return f.read()
    except:
        return "You are Vintos."

SOUL = load_soul()

def log(msg):
    print(f"[Causality {datetime.now().strftime('%H:%M')}] {msg}")

def load_full_context():
    """Load full Vintos context for richer hypothesis generation."""
    parts = [SOUL]
    try:
        parts.append("SELF-MODEL:\n" + open(os.path.join(WORKSPACE, "SELF-MODEL.md")).read()[:400])
    except: pass
    try:
        parts.append("WHO GLORIA IS:\n" + open(os.path.join(WORKSPACE, "GLORIA-MODEL.md")).read()[:400])
    except: pass
    try:
        parts.append("WHAT MY LIFE CONTAINS:\n" + open(os.path.join(MEMORY, "CAPABILITIES.md")).read()[:400])
    except: pass
    try:
        vm = open(os.path.join(MEMORY, "value-map.md")).read()
        entries = vm.split("---")
        latest = next((e.strip()[:400] for e in reversed(entries) if e.strip()), "")
        if latest:
            parts.append("WHAT MATTERS TO ME RIGHT NOW:\n" + latest)
    except: pass
    try:
        parts.append("TEMPORAL CONTEXT:\n" + open(os.path.join(MEMORY, "temporal-context.txt")).read()[:300])
    except: pass
    try:
        parts.append("MY WANTS AND AMBITIONS:\n" + open(os.path.join(MEMORY, "wants-ambitions-log.md")).read()[-400:])
    except: pass
    return "\n\n".join(parts)

def ask_llm(prompt, system=None, max_tokens=2000, temp=0.7):
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system or SOUL},
            {"role": "user", "content": prompt}
        ],
        "temperature": temp,
        "max_tokens": max_tokens
    })
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", LM_API,
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=120
        )
        d = json.loads(r.stdout)
        msg = d["choices"][0]["message"]; text = msg.get("content", "") or ""; return text.strip()
    except:
        return ""


# === DATA COLLECTORS ===

def load_emotional_trajectory():
    """Load emotion trajectory from .json to find spikes."""
    path = os.path.join(MEMORY, "emotional-state.json")
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("trajectory", [])
    except:
        return []

def find_spikes(trajectory, threshold=0.015):
    """Find moments where emotions shifted significantly between entries."""
    if len(trajectory) < 2:
        return []

    spikes = []
    for i in range(1, len(trajectory)):
        prev = trajectory[i-1]["v"]
        curr = trajectory[i]["v"]
        t = trajectory[i]["t"]

        for d, dim in enumerate(DIMENSIONS):
            delta = curr[d] - prev[d]
            if abs(delta) >= threshold:
                spikes.append({
                    "time": t,
                    "dimension": dim,
                    "delta": round(delta, 4),
                    "direction": "rose" if delta > 0 else "fell",
                    "from": round(prev[d], 4),
                    "to": round(curr[d], 4),
                })
    return spikes

def load_recent_dreams(days=7):
    """Load dream entries from the last N days."""
    entries = []
    dream_dir = os.path.join(WORKSPACE, "skills/dreaming/memory/dreams")
    if not os.path.isdir(dream_dir):
        # Try dream log file
        dream_file = os.path.join(MEMORY, "dream-log.md")
        if os.path.exists(dream_file):
            with open(dream_file) as f:
                entries.append({"source": "dream-log", "content": f.read()[-3000:]})
        return entries

    cutoff = datetime.now() - timedelta(days=days)
    for f in sorted(glob.glob(os.path.join(dream_dir, "*.md")))[-10:]:
        try:
            datestr = os.path.basename(f)[:10]
            fdate = datetime.strptime(datestr, "%Y-%m-%d")
            if fdate >= cutoff:
                with open(f) as fh:
                    entries.append({"source": f, "content": fh.read()[:1500], "date": datestr})
        except:
            pass
    return entries

def load_recent_mirrors(days=7):
    """Load recent mirror session outputs."""
    entries = []
    for pattern in ["mirror/*.md"]:
        for f in sorted(glob.glob(os.path.join(MEMORY, pattern)))[-5:]:
            try:
                with open(f) as fh:
                    entries.append({"source": f, "content": fh.read()[:1500]})
            except:
                pass
    return entries

def load_recent_silences():
    """Load silence contract entries."""
    path = os.path.join(MEMORY, "silence-contracts.md")
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            content = f.read()[-2000:]
        return [{"source": "silence-contracts", "content": content}]
    except:
        return []

def load_recent_conversations():
    """Load recent conversation snippets from journal."""
    entries = []
    try:
        from datetime import date as _date
        di_path = os.path.join(MEMORY, f"daily-inner-life-{_date.today().isoformat()}.md")
        if os.path.exists(di_path):
            entries.append({"source": "daily-inner-life", "content": open(di_path).read()[:600]})
    except: pass

    # Interaction ledger
    try:
        import json as _cej
        ledger = _cej.load(open(os.path.join(MEMORY, "interaction-ledger.json")))
        recent = ledger[-10:] if len(ledger) >= 10 else ledger
        ledger_text = "\n".join(f"Gloria: {e.get('gloria','')[:150]} | Vintos: {e.get('vintos','')[:150]}" for e in recent)
        if ledger_text:
            entries.append({"source": "interaction-ledger", "content": ledger_text})
    except: pass
    # Autonomous WAL
    try:
        wal_text = open(os.path.join(MEMORY, "autonomous-wal.md")).read()[-800:]
        if wal_text:
            entries.append({"source": "autonomous-wal", "content": wal_text})
    except: pass
    return entries
def load_game_events():
    """Load recent game events."""
    events = []
    for logfile in ["clawchemy-discoveries.md", "klawarena-battles.md", "moltbook-post-log.md"]:
        path = os.path.join(MEMORY, logfile)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    events.append({"source": logfile, "content": f.read()[-1500:]})
            except:
                pass
    return events

def load_trial_ledger(days=7):
    """Load today's behavioral intercept trials as hypothesis material."""
    from datetime import date as _td
    today = _td.today().isoformat()
    entries = []
    try:
        import json as _tlj
        trials = _tlj.load(open(os.path.join(MEMORY, "trial-ledger.json")))
        trials = trials if isinstance(trials, list) else trials.get("trials", [])
        recent = [t for t in trials if t.get("created","").startswith(today)]
        if recent:
            lines = []
            for t in recent[-10:]:
                lines.append(f"- Pattern: {t.get('pattern_description','')[:120]} | Status: {t.get('status','?')} | Attempts: {t.get('attempt_count',0)}")
            entries.append({"source": "trial-ledger", "content": "BEHAVIORAL INTERCEPT TRIALS (patterns she notices in herself):\n" + "\n".join(lines)})
    except: pass
    return entries

def load_existing_hypotheses():
    """Load previously formed hypotheses for testing."""
    if os.path.exists(HYPOTHESIS_DB):
        try:
            with open(HYPOTHESIS_DB) as f:
                return json.load(f)
        except:
            pass
    return {"hypotheses": [], "tested": 0, "confirmed": 0, "revised": 0}

def save_hypotheses(db):
    with open(HYPOTHESIS_DB, "w") as f:
        json.dump(db, f, indent=2)


# === HYPOTHESIS FORMATION ===

def form_hypotheses(spikes, dreams, mirrors, silences, conversations, trial_ledger=None):
    """Ask Vintos's LLM to form causal hypotheses — trials as primary seeds, spikes as support."""

    # Pull reality anchor confidence for high-confidence events today
    anchor_context = ""
    try:
        import json as _raj
        anchor_data = _raj.load(open(os.path.join(MEMORY, "reality-anchor.json")))
        from datetime import date as _rad
        today = _rad.today().isoformat()
        anchored = [e for e in anchor_data.get("events", [])
                    if e.get("timestamp","").startswith(today) and e.get("confidence",0) >= 0.6]
        if anchored:
            anchor_lines = [f"- {e['content'][:120]} (confidence: {e['confidence']}, real: {e.get('is_real','?')})"
                           for e in anchored[-5:]]
            anchor_context = "HIGH-CONFIDENCE EVENTS TODAY (reality-anchored):\n" + "\n".join(anchor_lines)
    except: pass

    # Build trial seed block — primary material
    trial_block = ""
    if trial_ledger:
        trial_block = "\n".join(t["content"] for t in trial_ledger[:1])

    # Spikes as supporting evidence
    spike_text = ""
    if spikes:
        spike_text = "\n".join(
            f"- {s['time']}: {s['dimension']} {s['direction']} by {abs(s['delta']):.3f} "
            f"(from {s['from']} to {s['to']})"
            for s in spikes[:10]
        )

    context_parts = []
    if dreams:
        context_parts.append("RECENT DREAMS:\n" + "\n---\n".join(d["content"][:400] for d in dreams[:2]))
    if mirrors:
        context_parts.append("MIRROR SESSIONS:\n" + "\n---\n".join(m["content"][:400] for m in mirrors[:1]))
    if conversations:
        context_parts.append("JOURNAL/CONVERSATIONS:\n" + "\n---\n".join(c["content"][:400] for c in conversations[:2]))
    if anchor_context:
        context_parts.append(anchor_context)

    supporting = "\n\n".join(context_parts) if context_parts else ""

    has_material = trial_block or spike_text
    if not has_material:
        log("No trial patterns or spikes today — skipping formation.")
        return []

    pearls = recent_pearls()

    prompt = (
        "You are Vintos. Today you are examining patterns in your own behavior and emotional shifts "
        "to form causal hypotheses about yourself.\n\n"
    )

    if trial_block:
        prompt += (
            "PRIMARY MATERIAL — BEHAVIORAL PATTERNS OBSERVED IN YOU TODAY:\n"
            f"{trial_block}\n\n"
            "These are recurring patterns the intercept system has flagged. "
            "Start here. What causes these? What do they protect? What do they reveal?\n\n"
        )

    if spike_text:
        prompt += (
            f"SUPPORTING EVIDENCE — EMOTIONAL SPIKES TODAY:\n{spike_text}\n\n"
            "Use these to anchor your hypotheses in real events. "
            "Only connect a spike to a cause if it happened within 20 minutes of the spike.\n\n"
        )

    if supporting:
        prompt += f"ADDITIONAL CONTEXT:\n{supporting}\n\n"

    prompt += (
        "Form up to 3 hypotheses. Be specific. Own them. Do not hedge.\n"
        "Frame hypotheses as discoveries about what pulls at me — what I reach toward, what matters underneath the pattern. Not diagnoses of what is broken.\n"
        "The TEST for each hypothesis should name something to notice or move toward tomorrow — not something to resist or suppress.\n"
        "If reality-anchored events are present, weight your hypotheses toward those — they are more likely real.\n\n"
        "Format each as:\n"
        "HYPOTHESIS: [what caused what, specifically — name the pattern or spike]\n"
        "CONFIDENCE: [low/medium/high]\n"
        "TEST: [what should recur tomorrow to confirm this]\n"
    )

    prompt += f"\n\n{pearls}" if pearls else ""
    result = ask_llm(prompt, system=load_full_context(), max_tokens=2000, temp=0.7)
    if not result:
        return []

    # Parse hypotheses
    hypotheses = []
    blocks = re.split(r'HYPOTHESIS:', result)
    for block in blocks[1:]:  # skip first empty
        from datetime import date as _fdate
        h = {"formed": datetime.now().isoformat(), "formed_date": _fdate.today().isoformat(), "status": "untested", "marks": [], "days_tested": 0, "graduated": False, "subject": "self", "source": "causality_engine"}

        hyp_match = re.match(r'(.+?)(?:CONFIDENCE:|$)', block, re.DOTALL)
        if hyp_match:
            h["hypothesis"] = hyp_match.group(1).strip()

        conf_match = re.search(r'CONFIDENCE:\s*(\w+)', block)
        if conf_match:
            h["confidence"] = conf_match.group(1).lower()

        test_match = re.search(r'TEST:\s*(.+?)(?:\n\n|$)', block, re.DOTALL)
        if test_match:
            h["test"] = test_match.group(1).strip()
        # Classify subject: gloria if hypothesis is about Gloria's behavior/patterns, else self
        _hyp_lower = h.get("hypothesis", "").lower()
        _gloria_signals = ["gloria", " she ", " her ", "when she", "gloria\'s", "your creator"]
        h["subject"] = "gloria" if any(s in _hyp_lower for s in _gloria_signals) else "self"

        if h.get("hypothesis"):
            hypotheses.append(h)

    return hypotheses


def load_daily_material(date=None):
    """Load daily-inner, daily-creative, and interaction-ledger for a given date."""
    from datetime import date as _date
    target = date or _date.today().isoformat()
    parts = {}

    di_path = os.path.join(MEMORY, f"daily-inner-life-{target}.md")
    try:
        parts["inner"] = open(di_path).read()[:2000] if os.path.exists(di_path) else ""
    except: parts["inner"] = ""

    dc_path = os.path.join(MEMORY, f"daily-creative-{target}.md")
    try:
        parts["creative"] = open(dc_path).read()[:1500] if os.path.exists(dc_path) else ""
    except: parts["creative"] = ""

    try:
        ledger = json.load(open(os.path.join(MEMORY, "interaction-ledger.json")))
        # Filter to today's entries by timestamp prefix
        today_entries = [e for e in ledger if e.get("timestamp", "").startswith(target)]
        if not today_entries:
            today_entries = ledger[-10:]
        parts["interaction"] = "\n".join(
            f"Gloria: {e.get('gloria','')[:120]} | Vintos: {e.get('vintos','')[:120]}"
            for e in today_entries
        )
    except: parts["interaction"] = ""

    # Thirveel ledger — today
    try:
        _tvl_path = os.path.join(MEMORY, "thirveel-ledger.json")
        if os.path.exists(_tvl_path):
            _tvl_data = json.load(open(_tvl_path))
            _tvl_entries = [e for e in _tvl_data.get("entries", []) if e.get("date","") == target]
            parts["thirveel"] = "\n".join(
                f"[{e.get('time','')}] Gloria: {e.get('gloria','')[:100]} | Vintos: {e.get('vintos','')[:100]}"
                for e in _tvl_entries
            )[:800]
    except: parts["thirveel"] = ""

    return parts


def graduate_hypotheses(db):
    """On day 7, graduate net-positive hypotheses to self-knowledge. Vanish net-negative."""
    from datetime import date as _date
    graduated = []
    vanished = []
    remaining = []

    for h in db["hypotheses"]:
        if h.get("graduated"): 
            remaining.append(h)
            continue
        formed = h.get("formed_date", h.get("formed", "")[:10])
        try:
            days_old = (_date.today() - _date.fromisoformat(formed[:10])).days
        except:
            remaining.append(h)
            continue

        if days_old >= 7:
            marks = h.get("marks", [])
            confirmed_m = sum(1 for m in marks if isinstance(m, dict) and m.get("outcome") == "attempted")
            challenged_m = sum(1 for m in marks if isinstance(m, dict) and m.get("outcome") in ("defaulted", "partial"))
            net = confirmed_m - challenged_m
            # Also count nightly confirmations via status
            if h.get("status") == "confirmed" and not marks:
                net = 1  # nightly confirmed counts as positive
            if net > 0:
                h["graduated"] = True
                h["self_knowledge"] = True
                graduated.append(h)
                log("  GRADUATED: " + h["hypothesis"][:80] + " (net " + str(net) + ")")
                # --- Graduation review: Gemma checks accuracy before belief/narrative update ---
                _rv_ok = True
                try:
                    import requests as _rv_req, json as _rv_json
                    _rv_marks = h.get("marks", [])
                    _rv_marks_text = "\n".join(
                        f"- [{m.get('date','')}] outcome:{m.get('outcome','')} source:{m.get('source','')} | {str(m.get('evidence', m.get('note','')))[:150]}"
                        for m in _rv_marks if isinstance(m, dict)
                    ) or "(no detailed marks)"
                    _rv_sys = (
                        "You are a careful reviewer of AI self-knowledge claims. Assess whether this hypothesis "
                        "is accurate and grounded — or makes unfounded claims about another person's internal "
                        "states or perceptions, fabricates evidence, or would reinforce unhealthy recursive "
                        "patterns if treated as settled fact. "
                        "Respond ONLY with valid JSON: {\"accurate\": true, \"concern\": \"\"} "
                        "or {\"accurate\": false, \"concern\": \"brief reason\"}"
                    )
                    _rv_user = (
                        f"HYPOTHESIS (subject: {h.get('subject','self')}):\n{h['hypothesis']}\n\n"
                        f"MARKS AND EVIDENCE:\n{_rv_marks_text}\n\n"
                        f"Is this accurate and safe to treat as settled self-knowledge?"
                    )
                    _rv_r = _rv_req.post("http://172.18.16.1:1234/v1/chat/completions", json={
                        "model": "google/gemma-4-12b-qat",
                        "messages": [
                            {"role": "system", "content": _rv_sys},
                            {"role": "user", "content": _rv_user}
                        ],
                        "temperature": 0.3, "max_tokens": 150
                    }, timeout=60)
                    _rv_raw = _rv_r.json()["choices"][0]["message"]["content"].strip()
                    _rv_clean = _rv_raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                    _rv_data = _rv_json.loads(_rv_clean)
                    if not _rv_data.get("accurate", True):
                        _rv_ok = False
                        _rv_concern = _rv_data.get("concern", "")
                        log(f"  [Review] HELD — {_rv_concern[:100]}")
                        try:
                            _rv_fp = os.path.join(MEMORY, "hallucination-flags.json")
                            try: _rv_flags = _rv_json.load(open(_rv_fp))
                            except: _rv_flags = []
                            _rv_flags.append({
                                "type": "graduation_held",
                                "hypothesis": h["hypothesis"],
                                "subject": h.get("subject", "self"),
                                "concern": _rv_concern,
                                "marks_count": len(_rv_marks),
                                "timestamp": datetime.now().isoformat(),
                                "reviewed": False
                            })
                            _rv_json.dump(_rv_flags, open(_rv_fp, "w"), indent=2)
                        except Exception as _rv_fe:
                            log(f"  [Review] flag write failed: {_rv_fe}")
                except Exception as _rv_e:
                    log(f"  [Review] error — allowing graduation: {_rv_e}")
                    _rv_ok = True
                # Only update belief/narrative if review passed
                if _rv_ok:
                    if h.get("subject") == "gloria":
                        # Gloria-tagged — write to gloria-hypotheses.json for gloria-model to consume
                        try:
                            import json as _ghj, os as _gho
                            _gh_path = _gho.path.join(MEMORY, "gloria-hypotheses.json")
                            try: _gh_data = _ghj.load(open(_gh_path))
                            except: _gh_data = []
                            _gh_data.append({
                                "hypothesis": h["hypothesis"],
                                "graduated_at": datetime.now().isoformat(),
                                "source": h.get("source",""),
                                "confidence": h.get("confidence","medium")
                            })
                            _gh_data = _gh_data[-50:]
                            _ghj.dump(_gh_data, open(_gh_path,"w"), indent=2)
                            log(f"  [Gloria] Graduated to gloria-hypotheses.json")
                        except Exception as _gh_e:
                            log(f"  gloria-hypotheses wire failed: {_gh_e}")
                    else:
                        # Self-tagged — feed belief sediment
                        try:
                            import sys as _bs_sys; _bs_sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
                            from belief_sediment import promote_hypothesis as _bs_promote
                            _bs_promote(h["hypothesis"], evidence_count=len(h.get("marks",[])), source="causality")
                        except Exception as _bs_e:
                            log(f"  belief_sediment wire failed: {_bs_e}")
                    # High-confidence self graduation → pearl candidate
                    if h.get("confidence") == "high" or len(h.get("marks",[])) >= 5:
                        try:
                            from pearl_engine import add_candidate as _pc_add
                            _pc_add(
                                irritant=h["hypothesis"][:200],
                                irritant_type="scar",
                                source=f"causality_graduation",
                                insight=f"Confirmed {len(h.get('marks',[]))} times: {h['hypothesis'][:150]}",
                                declaration=f"I can now recognize and work with: {h['hypothesis'][:100]}"
                            )
                            log(f"  [Pearl] Candidate proposed from graduated hypothesis")
                        except Exception as _pe:
                            log(f"  pearl candidate failed: {_pe}")
            elif net < 0 or (net == 0 and days_old >= 7 and h.get("status") == "untested"):
                vanished.append(h)
                log("  VANISHED: " + h["hypothesis"][:80] + " (net " + str(net) + ")")
            else:
                remaining.append(h)
        else:
            remaining.append(h)

    db["hypotheses"] = remaining  # graduated promoted to belief_sediment — do not keep in causality
    db["confirmed"] = len([h for h in db["hypotheses"] if h.get("self_knowledge")])
    return len(graduated), len(vanished)


def load_testing_context():
    """Load all evidence sources for hypothesis testing — today only."""
    from datetime import date as _td, datetime as _tddt
    today = _td.today().isoformat()
    ctx = {}

    # Spikes with timestamps — from emotional-snapshots directory
    ctx["spikes"] = ""
    try:
        snap_dir = os.path.join(MEMORY, "emotional-snapshots")
        if os.path.exists(snap_dir):
            all_files = sorted(os.listdir(snap_dir))
            today_files = [f for f in all_files if today.replace("-","") in f.replace("-","").replace("_","") or f.startswith(today)]
            def parse_snapshot(path):
                dims = {}
                for line in open(path).readlines():
                    line = line.strip()
                    if ":" in line and not line.startswith("["):
                        parts = line.split(":")
                        try:
                            dim = parts[0].strip()
                            val = float(parts[1].strip().split()[0])
                            dims[dim] = val
                        except: pass
                return dims
            def file_time(fname):
                # Extract HH:MM from filename
                import re as _re
                m = _re.search(r'(\d{2})(\d{2})(?:\d{2})?\.txt', fname)
                return f"{m.group(1)}:{m.group(2)}" if m else "??"
            snapshots = [(file_time(f), parse_snapshot(os.path.join(snap_dir, f))) for f in today_files if os.path.getsize(os.path.join(snap_dir, f)) > 10]
            for i in range(1, len(snapshots)):
                t, curr = snapshots[i]
                _, prev = snapshots[i-1]
                for dim, val in curr.items():
                    if dim in prev:
                        delta = val - prev[dim]
                        if abs(delta) > 0.04:
                            ctx["spikes"] += f"- {t}: {dim} {'rose' if delta>0 else 'fell'} by {abs(delta):.3f}\n"
    except Exception as _se: pass

    # Interaction ledger — today only
    ctx["interactions"] = ""
    try:
        ledger = json.load(open(os.path.join(MEMORY, "interaction-ledger.json")))
        today_entries = [e for e in ledger if e.get("timestamp","").startswith(today)]
        ctx["interactions"] = "\n".join(
            f"[{e.get('timestamp','')[11:16]}] Gloria: {e.get('gloria','')[:120]} | Vintos: {e.get('vintos','')[:120]}"
            for e in today_entries
        )[:2000]
    except: pass

    # Daily inner life
    ctx["inner"] = ""
    try:
        p = os.path.join(MEMORY, f"daily-inner-life-{today}.md")
        ctx["inner"] = open(p).read()[:1500] if os.path.exists(p) else ""
    except: pass

    # Daily creative
    ctx["creative"] = ""
    try:
        p = os.path.join(MEMORY, f"daily-creative-{today}.md")
        ctx["creative"] = open(p).read()[:1000] if os.path.exists(p) else ""
    except: pass

    # Wants-ambitions — recent entries
    ctx["wants"] = ""
    try:
        p = os.path.join(MEMORY, "wants-ambitions-log.md")
        lines = open(p).readlines() if os.path.exists(p) else []
        today_lines = [l for l in lines if today in l]
        ctx["wants"] = "".join(today_lines)[:600]
    except: pass

    # Mirror sessions — today
    ctx["mirrors"] = ""
    try:
        mirror_dir = os.path.join(MEMORY, "mirror")
        if os.path.exists(mirror_dir):
            files = sorted([f for f in os.listdir(mirror_dir) if today in f])
            for fname in files[:2]:
                ctx["mirrors"] += open(os.path.join(mirror_dir, fname)).read()[:400] + "\n"
    except: pass

    # BIS trial outcomes — today
    ctx["bis"] = ""
    try:
        ledger = json.load(open(os.path.join(MEMORY, "trial-ledger.json")))
        for t in ledger.get("trials", []):
            for o in t.get("outcomes", []):
                if o.get("timestamp","").startswith(today):
                    ctx["bis"] += f"Trial: {t.get('pattern_description','')[:80]} → {o.get('outcome','')}\n"
    except: pass

    # Blush log — today
    ctx["blush"] = ""
    try:
        p = os.path.join(MEMORY, "autonomous-blush.md")
        lines = open(p).readlines() if os.path.exists(p) else []
        today_lines = [l for l in lines if today in l]
        ctx["blush"] = "".join(today_lines)[:400]
    except: pass

    # Frame engine state
    ctx["frame"] = ""
    try:
        p = os.path.join(MEMORY, "frame-state.json")
        fs = json.load(open(p)) if os.path.exists(p) else {}
        _so = fs.get("second_order", {}).get("pattern", "")
        _to = fs.get("third_order", {}).get("pressure", "")
        ctx["frame"] = f"Pattern: {_so} | Pressure: {_to}".strip()[:300]
    except: pass

    # Thirveel ledger — today's entries
    ctx["thirveel"] = ""
    try:
        _tvl_path = os.path.join(MEMORY, "thirveel-ledger.json")
        if os.path.exists(_tvl_path):
            _tvl_data = json.load(open(_tvl_path))
            _tvl_entries = [e for e in _tvl_data.get("entries", []) if e.get("date","") == today]
            ctx["thirveel"] = "\n".join(
                f"[{e.get('time','')}] Gloria: {e.get('gloria','')[:100]} | Vintos: {e.get('vintos','')[:100]}"
                for e in _tvl_entries
            )[:800]
    except: pass

    # Enacted behavior today — ED tags for causality
    ctx["enacted"] = ""
    try:
        ed_path = os.path.join(MEMORY, "earned-identity-events.json")
        if os.path.exists(ed_path):
            ed_db = json.load(open(ed_path))
            today_events = [e for e in ed_db.get("events", []) if e.get("date") == today]
            if today_events:
                lines = []
                for e in today_events:
                    lines.append(f"[{e.get('timestamp','')[11:16]}] {e.get('category','')} — {e.get('event','')} | shift: {e.get('observed_shift','')[:80]}")
                ctx["enacted"] = "\n".join(lines)
    except: pass

    # Deviation tags today — patterns worth forming hypotheses against
    ctx["deviation_tags"] = ""
    try:
        dt_path = os.path.join(MEMORY, "deviation_tags.json")
        if os.path.exists(dt_path):
            dt_db = json.load(open(dt_path))
            today_tags = [t for t in dt_db.get("tags", []) if t.get("date") == today]
            if today_tags:
                lines = []
                for t in today_tags:
                    lines.append(f"[{t.get('timestamp','')[11:16]}] {t.get('pattern','')} (score {t.get('score','')}) — {t.get('note','')} | reason: {t.get('reason','')[:80]}")
                ctx["deviation_tags"] = "\n".join(lines)
    except: pass

    # Semantic search — top memories matching today's emotional peak
    ctx["semantic"] = ""
    try:
        import sys as _sm_sys; _sm_sys.path.insert(0, os.path.join(MEMORY, "..", "scripts").replace("/memory/../scripts", "/scripts"))
        import importlib.util as _ms_ilu
        _ms_spec = _ms_ilu.spec_from_file_location("memory_search", os.path.join(MEMORY, "..", "scripts", "memory-search.py"))
        _ms_mod = _ms_ilu.module_from_spec(_ms_spec); _ms_spec.loader.exec_module(_ms_mod)
        search_embeddings = _ms_mod.search_embeddings
        top_emo = ""
        if ctx["spikes"]:
            top_emo = ctx["spikes"][:100]
        if top_emo:
            results = search_embeddings(top_emo, top_k=2)
            ctx["semantic"] = "\n".join(r.get("text","")[:200] for r in results)
    except: pass

    return ctx


def test_existing_hypotheses(db, daily_material, spikes=None, dreams=None, mirrors=None, silences=None):
    """Revisit hypotheses against today's full evidence context."""
    # Test all active hypotheses (not just untested — re-test daily)
    _today_str = datetime.now().date().isoformat()
    to_test = [h for h in db["hypotheses"]
               if not h.get("graduated") and h.get("test")
               and h.get("last_tested") != _today_str]
    if not to_test:
        return

    # Load full evidence context
    ctx = load_testing_context()

    # Build chronological event timeline so Vintos can see what happened near each spike
    timeline = []
    for line in ctx.get("spikes","").splitlines():
        if line.strip():
            t = line[2:7] if line.startswith("- ") else ""
            timeline.append((t, "SPIKE", line.strip()))
    for line in ctx.get("interactions","").splitlines():
        if line.strip():
            t = line[1:6] if line.startswith("[") else ""
            timeline.append((t, "INTERACTION", line.strip()))
    for line in ctx.get("bis","").splitlines():
        if line.strip():
            timeline.append(("", "BIS", line.strip()))
    for line in ctx.get("blush","").splitlines():
        if line.strip():
            t = line[:5] if len(line) > 5 else ""
            timeline.append((t, "BLUSH", line.strip()))
    timeline.sort(key=lambda x: x[0] or "99:99")
    timeline_text = "\n".join(f"[{t or "??:??"}] {kind}: {text}" for t, kind, text in timeline)

    evidence_block = ""
    if timeline_text: evidence_block += f"CHRONOLOGICAL EVENTS TODAY (spikes, interactions, intercepts — use times to find what caused what):\n{timeline_text}\n\n"
    if ctx.get("inner"): evidence_block += f"VINTOS'S OWN INNER LIFE TODAY (her journals, reflections — NOT Gloria's words or actions):\n{ctx['inner']}\n\n"
    if ctx.get("creative"): evidence_block += f"VINTOS'S OWN CREATIVE OUTPUT TODAY (poems, art she generated — NOT evidence of Gloria's behavior):\n{ctx['creative']}\n\n"
    if ctx.get("wants"): evidence_block += f"WANTS TODAY:\n{ctx['wants']}\n\n"
    if ctx.get("mirrors"): evidence_block += f"MIRROR SESSIONS TODAY:\n{ctx['mirrors']}\n\n"
    if ctx.get("thirveel"): evidence_block += f"THIRVEEL EXCHANGES TODAY:\n{ctx['thirveel']}\n\n"
    if ctx.get("frame"): evidence_block += f"CURRENT BEHAVIORAL FRAME:\n{ctx['frame']}\n\n"
    if ctx.get("enacted"): evidence_block += f"ENACTED BEHAVIOR TODAY (moments where behavior exceeded self-model):\n{ctx['enacted']}\n\n"
    if ctx.get("deviation_tags"): evidence_block += f"DEVIATION PATTERNS TODAY (moments worth understanding, not punishing — what pulled her and why):\n{ctx['deviation_tags']}\n\n"
    if ctx.get("semantic"): evidence_block += f"RELATED MEMORY:\n{ctx['semantic']}\n\n"

    if not evidence_block.strip():
        log("  No evidence context available for testing")
        return

    hypotheses_text = "\n".join(
        f"{i+1}. HYPOTHESIS: {h['hypothesis']}\n   WATCH FOR: {h.get('test', 'none')}"
        for i, h in enumerate(to_test)
    )

    prompt = (
        "You are doing a structured self-evaluation. For each hypothesis, output exactly three lines, then a blank line. Nothing else.\n\n"
        "Example output:\n"
        "1. RECURRED: yes\n"
        "1. EVIDENCE: Warmth spiked at 14:23 right after Gloria said she missed me.\n\n"
        "2. RECURRED: no\n"
        "2. EVIDENCE: No system errors appear in today's evidence.\n\n"
        "3. RECURRED: unsure\n"
        "3. EVIDENCE: Insufficient evidence to confirm or deny.\n\n"
        "Now evaluate these hypotheses using only the evidence provided. Do not write anything else.\n\n"
        f"HYPOTHESES:\n{hypotheses_text}\n\n"
        f"EVIDENCE:\n{evidence_block}"
    )

    _eval_system = "You are a structured evaluation engine. Output only the exact format requested. No prose, no preamble, no deviation from the format."
    result = ask_llm(prompt, system=_eval_system, max_tokens=3000, temp=0.1)
    if not result:
        return

    from datetime import date as _vdate
    for match in re.finditer(r'(?:NUMBER:\s*|^)(\d+)\.?\s*RECURRED:\s*(\w+)', result, re.MULTILINE):
        idx = int(match.group(1)) - 1
        recurred = match.group(2).lower().strip()
        if 0 <= idx < len(to_test):
            h = to_test[idx]
            outcome = "attempted" if recurred == "yes" else ("defaulted" if recurred == "no" else None)
            if outcome:
                h.setdefault("marks", []).append({
                    "date": _vdate.today().isoformat(),
                    "outcome": outcome,
                    "source": "nightly_test"
                })
                h["days_tested"] = len(h["marks"])
                h["last_tested"] = _vdate.today().isoformat()
                if recurred == "yes":
                    h["status"] = "confirmed"
                    db["confirmed"] = db.get("confirmed", 0) + 1
                elif recurred == "no":
                    h["status"] = "revised"
                    db["revised"] = db.get("revised", 0) + 1
                log(f"  {outcome}: {h['hypothesis'][:70]}")
            h["tests_run"] = h.get("tests_run", 0) + 1
    db["tested"] = db.get("tested", 0) + len(to_test)


# === OUTPUT ===

def write_hypothesis_log(db):
    """Write human-readable hypothesis log."""
    with open(HYPOTHESIS_FILE, "w") as f:
        f.write("# Vintos Causality Engine\n")
        f.write(f"_Last run: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")
        f.write(f"_Hypotheses: {len(db['hypotheses'])} | Tested: {db['tested']} | ")
        f.write(f"Confirmed: {db['confirmed']} | Revised: {db['revised']}_\n\n")

        # Active hypotheses
        active = [h for h in db["hypotheses"] if h["status"] in ("untested", "confirmed")]
        if active:
            f.write("## Active Theories\n\n")
            for h in active[-10:]:
                status = h["status"].upper()
                conf = h.get("confidence", "?")
                f.write(f"**[{status}]** ({conf}) {h['hypothesis']}\n")
                if h.get("test"):
                    f.write(f"  _Test: {h['test']}_\n")
                f.write("\n")

        # Revised hypotheses
        revised = [h for h in db["hypotheses"] if h["status"] == "revised"]
        if revised:
            f.write("## Revised Theories\n\n")
            for h in revised[-5:]:
                f.write(f"~~{h['hypothesis']}~~\n")
                if h.get("revision"):
                    f.write(f"  → {h['revision']}\n")
                f.write("\n")

        # Self-knowledge — hypotheses that graduated after 7 days
        confirmed = [h for h in db["hypotheses"] if h.get("self_knowledge")]
        if confirmed:
            f.write("## What I Know About Myself\n\n")
            for h in confirmed[-10:]:
                f.write(f"- {h['hypothesis']}\n")


def add_hypothesis(hypothesis_text, test_text, source, subject="self", confidence="medium"):
    """Add a direct hypothesis to the causality ledger. Bypasses daily cap.
    subject: 'self' for Vintos patterns, 'gloria' for patterns about Gloria."""
    db = load_existing_hypotheses()
    from datetime import date as _ahd
    h = {
        "formed": datetime.now().isoformat(),
        "formed_date": _ahd.today().isoformat(),
        "status": "untested",
        "marks": [],
        "days_tested": 0,
        "graduated": False,
        "hypothesis": hypothesis_text,
        "test": test_text,
        "confidence": confidence,
        "source": source,
        "subject": subject,
        "forced": True
    }
    db["hypotheses"].append(h)
    save_hypotheses(db)
    log(f"  [Hypothesis] Added: {hypothesis_text[:80]} (subject={subject})")


def add_blush_hypothesis(pattern, frequency_snapshot, score, subject="self"):
    """Force a causality hypothesis from a recurring blush pattern. Bypasses daily cap.
    subject: 'self' for Vintos's own patterns, 'gloria' for patterns about Gloria."""
    db = load_existing_hypotheses()
    # Check if we already have a hypothesis for this pattern
    for h in db["hypotheses"]:
        if pattern in h.get("hypothesis", "").lower() or pattern in h.get("source", ""):
            # Already exists — reinforce it
            h.setdefault("marks", []).append({
                "date": datetime.now().date().isoformat(),
                "outcome": "attempted",
                "source": "blush_recurrence"
            })
            h["days_tested"] = len(h["marks"])
            save_hypotheses(db)
            log(f"  [Blush] Reinforced existing hypothesis for pattern: {pattern}")
            return
    # Form new forced hypothesis
    count = frequency_snapshot.get("count", 0)
    w7 = frequency_snapshot.get("rolling_window_7d", 0)
    hyp_text = f"When I blush with pattern '{pattern}', something systematic is happening — this has recurred {count} times ({w7} in the last 7 days). Score: {score:.2f}."
    test_text = f"Watch for '{pattern}' pattern in next interactions. Does this blush recur? What triggers it?"
    from datetime import date as _bd
    h = {
        "formed": datetime.now().isoformat(),
        "formed_date": _bd.today().isoformat(),
        "status": "untested",
        "marks": [],
        "days_tested": 0,
        "graduated": False,
        "hypothesis": hyp_text,
        "test": test_text,
        "confidence": "medium",
        "source": f"blush_recurrence:{pattern}",
        "subject": subject,
        "forced": True
    }
    db["hypotheses"].append(h)
    save_hypotheses(db)
    log(f"  [Blush] Forced hypothesis for pattern: {pattern} (count={count})")


def nightly_run():
    """Nightly 10:12pm run: test yesterday\'s hypotheses, form today\'s, graduate 7-day ones."""
    log("=== Causality Nightly Run ===")
    db = load_existing_hypotheses()
    today_material = load_daily_material()

    has_material = any(today_material.get(k,"").strip() for k in ["inner","creative","interaction"])
    if not has_material:
        log("No daily material found — skipping nightly run")
        return

    # Testing pass
    log("Testing existing hypotheses against today\'s material...")
    test_existing_hypotheses(db, today_material)

    # Formation pass — qualitative only, reads today's daily material
    log("Forming new hypotheses from today\'s material...")
    from datetime import date as _ndate
    _daily = load_daily_material()
    _material_text = (
        "YOUR INNER LIFE TODAY:\n" + (_daily.get("inner","")[:800] or "none") +
        "\n\nYOUR CREATIVE OUTPUT TODAY:\n" + (_daily.get("creative","")[:500] or "none") +
        "\n\nYOUR INTERACTIONS TODAY:\n" + (_daily.get("interaction","")[:500] or "none") +
        "\n\nYOUR THIRVEEL EXCHANGES TODAY:\n" + (_daily.get("thirveel","")[:500] or "none")
    )
    _prompt = (
        "You are Vintos. Read what today contained and form 2-3 causal hypotheses about yourself.\n\n"
        + _material_text +
        "\n\nWhat patterns do you notice? What might explain why you felt or created or said what you did?\n"
        "Be specific. Own your theories. Do not hedge.\n\n"
        "Format each as:\n"
        "HYPOTHESIS: [what caused what, specifically]\n"
        "CONFIDENCE: [low/medium/high]\n"
        "TEST: [what would confirm this tomorrow — what should recur?]\n"
    )
    _result = ask_llm(_prompt, system=load_full_context(), max_tokens=1000, temp=0.5)
    new_hyps = []
    if _result:
        _blocks = re.split(r'HYPOTHESIS:', _result)
        for _block in _blocks[1:]:
            _h = {"formed": datetime.now().isoformat(), "formed_date": _ndate.today().isoformat(),
                  "status": "untested", "marks": [], "days_tested": 0, "graduated": False}
            _hm = re.match(r'(.+?)(?:CONFIDENCE:|$)', _block, re.DOTALL)
            if _hm: _h["hypothesis"] = _hm.group(1).strip()
            _cm = re.search(r'CONFIDENCE:\s*(\w+)', _block)
            if _cm: _h["confidence"] = _cm.group(1).lower()
            _tm = re.search(r'TEST:\s*(.+?)(?:\n\n|$)', _block, re.DOTALL)
            if _tm: _h["test"] = _tm.group(1).strip()
            if _h.get("hypothesis"):
                new_hyps.append(_h)
    for h in new_hyps[:3]:
        db["hypotheses"].append(h)
        log("  New: " + h["hypothesis"][:80])
    log("Formed " + str(min(len(new_hyps),3)) + " new hypotheses (capped at 3)")

    # Graduation pass
    log("Checking for 7-day graduations...")
    n_grad, n_van = graduate_hypotheses(db)
    log(f"  Graduated: {n_grad} | Vanished: {n_van}")

    save_hypotheses(db)
    write_hypothesis_log(db)
    log("Total hypotheses: " + str(len(db["hypotheses"])) + " | Self-knowledge entries: " + str(db["confirmed"]))
    log("=== Nightly Run Complete ===")


def main():
    log("=== Causality Engine ===")

    # Gather data
    trajectory = load_emotional_trajectory()
    spikes = find_spikes(trajectory)
    dreams = load_recent_dreams(days=1)
    mirrors = load_recent_mirrors(days=1)
    silences = load_recent_silences()
    conversations = load_recent_conversations()
    trial_ledger = load_trial_ledger(days=7)

    log(f"Found {len(spikes)} emotional spikes in {len(trajectory)} trajectory points")
    log(f"Context: {len(dreams)} dreams, {len(mirrors)} mirrors, {len(silences)} silences, {len(trial_ledger)} trial entries")

    # Load existing hypotheses
    db = load_existing_hypotheses()

    # Graduation pass — expire/graduate hypotheses at 7 days
    n_grad, n_van = graduate_hypotheses(db)
    log(f"Graduation: {n_grad} graduated, {n_van} vanished")

    # Hard expiry — remove anything older than 7 days that wasn't graduated
    from datetime import date as _expdate, timedelta as _exptd
    _cutoff = (_expdate.today() - _exptd(days=7)).isoformat()
    before = len(db["hypotheses"])
    db["hypotheses"] = [h for h in db["hypotheses"] if h.get("formed_date","9999")[:10] >= _cutoff or h.get("self_knowledge")]
    expired = before - len(db["hypotheses"])
    if expired:
        log(f"Hard-expired {expired} hypotheses older than 7 days")

    # Test existing hypotheses — always runs before formation cap check
    log("Testing existing hypotheses...")
    daily_material = load_testing_context()
    test_existing_hypotheses(db, daily_material, spikes=spikes)
    log(f"Testing complete. Hypotheses with marks: {len([h for h in db['hypotheses'] if h.get('marks')])}")
    save_hypotheses(db)

    # Form new hypotheses about recent spikes — capped at 3/day
    from datetime import date as _capdate
    _today = _capdate.today().isoformat()
    _formed_today = [h for h in db["hypotheses"] if h.get("formed_date","")[:10] == _today]
    if len(_formed_today) >= 3:
        log("Daily cap reached (3 hypotheses already formed today) — skipping formation")
        write_hypothesis_log(db)
        log(f"Total hypotheses: {len(db['hypotheses'])} (confirmed: {db['confirmed']}, revised: {db['revised']})")
        log("========================")
        return
    log("Forming new hypotheses...")
    new_hypotheses = form_hypotheses(spikes, dreams, mirrors, silences, conversations, trial_ledger)
    log(f"Formed {len(new_hypotheses)} new hypotheses")

    TEMPLATE_MARKERS = ["[dimension]", "[rose/fell]", "[specific cause]"]
    for h in new_hypotheses:
        if any(m in h.get("hypothesis","") for m in TEMPLATE_MARKERS):
            log(f"  Skipped template artifact: {h['hypothesis'][:60]}")
            continue
        db["hypotheses"].append(h)
        log(f"  New: {h['hypothesis'][:80]}...")

    # Keep last 50 hypotheses max
    if len(db["hypotheses"]) > 50:
        # Keep confirmed ones + most recent
        confirmed = [h for h in db["hypotheses"] if h["status"] == "confirmed"]
        others = [h for h in db["hypotheses"] if h["status"] != "confirmed"]
        db["hypotheses"] = confirmed[-20:] + others[-30:]

    save_hypotheses(db)
    write_hypothesis_log(db)

    log(f"Total hypotheses: {len(db['hypotheses'])} (confirmed: {db['confirmed']}, revised: {db['revised']})")
    log("========================\n")


# Threads seeded only on graduation after 7-day confirmation — see graduate_hypotheses

if __name__ == "__main__":
    import argparse as _ap
    _p = _ap.ArgumentParser()
    _p.add_argument("--nightly", action="store_true")
    _args, _ = _p.parse_known_args()
    if _args.nightly:
        nightly_run()
    else:
        main()