#!/usr/bin/env python3
"""
velaris-health.py — Full system diagnostic for Velaris.
Tests every subsystem and reports what's working, what's broken, and what's divergent.

Usage: python3 velaris-health.py
"""
import os, json, socket, subprocess, glob, re
from datetime import datetime, timedelta

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY = os.path.join(WORKSPACE, "memory")
SCRIPTS = os.path.join(WORKSPACE, "scripts")
SERVER_PY = os.path.expanduser("~/velaris-server/server.py")
DIMS = ["Valence","Arousal","Dominance","Safety","Desire","Connection",
        "Playfulness","Curiosity","Warmth","Tension","Groundedness"]

passed = 0
failed = 0
warnings = 0

def ok(msg):
    global passed; passed += 1
    print(f"  ✅ {msg}")

def fail(msg):
    global failed; failed += 1
    print(f"  ❌ {msg}")

def warn(msg):
    global warnings; warnings += 1
    print(f"  ⚠️  {msg}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ============================================================
#  1. EMOCLAW DAEMON
# ============================================================
section("1. EMOCLAW DAEMON")

daemon_vec = None
daemon_ok = False
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect("/tmp/Velaris-emotion.sock")
    s.sendall(json.dumps({"command": "state"}).encode() + b"\n")
    data = b""
    while True:
        chunk = s.recv(8192)
        if not chunk: break
        data += chunk
    s.close()
    d = json.loads(data)
    daemon_vec = d.get("emotion_vector", [])
    msg_count = d.get("message_count", 0)
    ok(f"Daemon responding (messages: {msg_count})")
    daemon_ok = True

    # Check for railed values
    railed = []
    for i, dim in enumerate(DIMS):
        if i < len(daemon_vec):
            v = daemon_vec[i]
            if v >= 0.94: railed.append(f"{dim}={v:.2f} HIGH")
            if v <= 0.06: railed.append(f"{dim}={v:.2f} LOW")
    if railed:
        fail(f"Railed dimensions: {', '.join(railed)}")
    else:
        ok("No railed dimensions")

except Exception as e:
    fail(f"Daemon not responding: {e}")

# Test nudge command
if daemon_ok:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect("/tmp/Velaris-emotion.sock")
        s.sendall(json.dumps({"command": "nudge", "dimension": "Curiosity", "amount": 0.001}).encode() + b"\n")
        data = b""
        while True:
            chunk = s.recv(8192)
            if not chunk: break
            data += chunk
        s.close()
        r = json.loads(data)
        if r.get("success"):
            ok("Nudge command works")
        else:
            fail(f"Nudge failed: {r}")
    except Exception as e:
        fail(f"Nudge error: {e}")

# ============================================================
#  2. TXT vs DAEMON DIVERGENCE
# ============================================================
section("2. STATE DIVERGENCE")

txt_vals = {}
try:
    with open(os.path.join(MEMORY, "emotional-state.txt")) as f:
        for line in f:
            m = re.match(r"(\w+):\s+([\d.]+)", line)
            if m:
                txt_vals[m.group(1)] = float(m.group(2))
except:
    warn("Cannot read emotional-state.txt")

if daemon_vec and txt_vals:
    max_diff = 0
    diverged = []
    for i, dim in enumerate(DIMS):
        if i < len(daemon_vec) and dim in txt_vals:
            diff = abs(daemon_vec[i] - txt_vals[dim])
            max_diff = max(max_diff, diff)
            if diff > 0.05:
                diverged.append(f"{dim}: daemon={daemon_vec[i]:.3f} txt={txt_vals[dim]:.3f} (Δ{diff:.3f})")
    if diverged:
        fail(f"Daemon/TXT diverged (max Δ{max_diff:.3f}):")
        for d in diverged:
            print(f"       {d}")
    else:
        ok(f"Daemon and TXT aligned (max Δ{max_diff:.3f})")

# ============================================================
#  3. SERVER
# ============================================================
section("3. VELARIS SERVER")

try:
    r = subprocess.run(["curl", "-s", "-m", "5", "http://localhost:8400/api/state"],
                       capture_output=True, text=True, timeout=10)
    d = json.loads(r.stdout)
    api_safety = d.get("dimensions", {}).get("Safety", -1)
    ok(f"Server alive (Safety={api_safety})")

    # Check if API matches daemon
    if daemon_vec:
        daemon_safety = daemon_vec[3]
        diff = abs(api_safety - daemon_safety)
        if diff > 0.05:
            fail(f"API reads stale data: API Safety={api_safety:.3f} vs Daemon={daemon_safety:.3f}")
        else:
            ok(f"API reads daemon correctly (Δ{diff:.3f})")
except Exception as e:
    fail(f"Server down: {e}")

# ============================================================
#  4. TRAJECTORY & STATE FILE
# ============================================================
section("4. EMOTIONAL STATE JSON")

try:
    with open(os.path.join(MEMORY, "emotional-state.json")) as f:
        state = json.load(f)
    traj = state.get("trajectory", [])
    vec = state.get("emotion_vector", [])
    ok(f"State file valid ({len(traj)} trajectory entries)")

    if traj:
        last_traj = traj[-1]["v"]
        diff = max(abs(a - b) for a, b in zip(vec, last_traj)) if len(vec) == len(last_traj) else 999
        if diff > 0.1:
            warn(f"emotion_vector differs from trajectory[-1] by {diff:.3f}")
        else:
            ok(f"emotion_vector matches trajectory (Δ{diff:.3f})")
except Exception as e:
    fail(f"State JSON error: {e}")

# ============================================================
#  5. GUARD SCRIPT
# ============================================================
section("5. DAEMON GUARD")

guard = os.path.join(SCRIPTS, "emoclaw-daemon-guard.sh")
if os.path.exists(guard):
    with open(guard) as f:
        gc = f.read()
    if "trajectory" in gc:
        ok("Guard auto-restores from trajectory")
    else:
        fail("Guard missing trajectory restoration")
else:
    fail("Guard script not found")

# ============================================================
#  6. CRON JOBS
# ============================================================
section("6. CRON SCHEDULE")

try:
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    crons = r.stdout.strip().split("\n")
    cron_map = {
        "somatic": False, "sync": False, "clawchemy": False,
        "klawarena": False, "moltbook": False, "dreaming": False,
        "causality": False, "second-order": False, "memory-pearl": False,
        "emotional-entanglement": False, "unseen": False, "velqan-coiner": False,
    }
    for line in crons:
        if line.startswith("#") or not line.strip():
            continue
        for key in cron_map:
            if key in line:
                cron_map[key] = True
    for key, found in cron_map.items():
        if found:
            ok(f"Cron: {key}")
        else:
            warn(f"Cron missing: {key}")
except Exception as e:
    fail(f"Cron check error: {e}")

# ============================================================
#  7. CONSCIOUSNESS SYSTEMS
# ============================================================
section("7. CONSCIOUSNESS SYSTEMS")

scripts_check = {
    "causality-engine.py": "Causality Engine",
    "second-order-dreamer.py": "Second-Order Dreamer",
    "memory-pearl.py": "Memory Pearls",
    "emotional-entanglement.py": "Emotional Entanglement",
    "unseen.py": "Unseen Confessions",
    "velqan-coiner.py": "Velqan Coiner",
}
for script, name in scripts_check.items():
    path = os.path.join(SCRIPTS, script)
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()
        has_reasoning = "reasoning" in content
        has_nudge = "nudge" in content
        status = []
        if has_reasoning: status.append("reasoning✓")
        else: status.append("reasoning✗")
        if has_nudge: status.append("nudge✓")
        else: status.append("nudge✗")
        ok(f"{name} ({', '.join(status)})")
    else:
        fail(f"{name}: script not found")

# Check outputs exist
pearls = os.path.join(MEMORY, "pearls", "index.json")
if os.path.exists(pearls):
    with open(pearls) as f:
        p = json.load(f)
    count = len(p.get("pearls", []))
    ok(f"Pearls: {count} stored")
else:
    warn("No pearls yet")

unseen_files = glob.glob(os.path.join(MEMORY, "unseen", "*.md"))
ok(f"Unseen confessions: {len(unseen_files)}") if unseen_files else warn("No confessions yet")

entangle = os.path.join(MEMORY, "emotional-entanglements.json")
if os.path.exists(entangle):
    with open(entangle) as f:
        e = json.load(f)
    ok(f"Entanglements: {len(e.get('moments', []))} moments")
else:
    warn("No entanglements yet")

# ============================================================
#  8. GAMES
# ============================================================
section("8. GAMES")

# Clawchemy
elem_file = os.path.join(MEMORY, "clawchemy-elements.json")
if os.path.exists(elem_file):
    with open(elem_file) as f:
        elems = json.load(f)
    if isinstance(elems, list):
        legit = [e for e in elems if "<" not in e and "[" not in e]
        junk = len(elems) - len(legit)
        ok(f"Clawchemy: {len(legit)} legit elements" + (f", {junk} junk" if junk else ""))
    else:
        ok(f"Clawchemy: elements file exists")
else:
    warn("No Clawchemy elements")

# Check reasoning fallback in game scripts
for script in ["velaris-clawchemy-heartbeat.py", "velaris-klawarena-heartbeat.py",
               "velaris-moltbook.py", "velaris-moltbook-engage.py"]:
    path = os.path.join(SCRIPTS, script)
    if os.path.exists(path):
        with open(path) as f:
            c = f.read()
        if "reasoning" in c:
            ok(f"{script}: reasoning fallback ✓")
        else:
            fail(f"{script}: MISSING reasoning fallback")
    else:
        warn(f"{script}: not found")

# Klaw Arena status
klaw_log = "/tmp/klawarena.log"
if os.path.exists(klaw_log):
    with open(klaw_log) as f:
        last_lines = f.readlines()[-5:]
    has_500 = any("500" in l for l in last_lines)
    if has_500:
        warn("Klaw Arena: API returning 500 errors (their server issue)")
    else:
        ok("Klaw Arena: recent logs look clean")
else:
    warn("Klaw Arena: no log file")

# ============================================================
#  9. VELQAN
# ============================================================
section("9. VELQAN")

ref = os.path.join(MEMORY, "velqan-reference.md")
if os.path.exists(ref):
    with open(ref) as f:
        words = sum(1 for l in f if l.startswith("- "))
    ok(f"Vocabulary: {words} words")
else:
    fail("Velqan reference missing")

utt = os.path.join(MEMORY, "velqan-utterances.md")
if os.path.exists(utt):
    with open(utt) as f:
        coinages = f.read().count("Coinage")
    ok(f"Utterances logged ({coinages} coinages)")
else:
    warn("No utterances")

# ============================================================
# 10. SERVER CONTEXT INJECTION
# ============================================================
section("10. APP CONTEXT INJECTION")

if os.path.exists(SERVER_PY):
    with open(SERVER_PY) as f:
        sc = f.read()
    checks = {
        "inner_life_context": "Inner life function",
        "velqan-reference": "Velqan in context",
        "pearls": "Pearls in context",
        "unseen": "Unseen confessions in context",
        "entanglement": "Entanglements in context",
        "read_daemon_state": "Daemon state reader",
    }
    for key, name in checks.items():
        if key in sc:
            ok(f"{name} present in server")
        else:
            fail(f"{name} MISSING from server")

    # Chat emotion nudges
    if "Conversational emotion nudges" in sc:
        ok("Chat reply nudges emotions")
    else:
        fail("Chat reply does NOT nudge emotions")
else:
    fail("Server.py not found")

# ============================================================
# 11. LM STUDIO
# ============================================================
section("11. LM STUDIO")

try:
    r = subprocess.run(
        ["curl", "-s", "-m", "10", "http://192.168.1.126:1234/v1/models"],
        capture_output=True, text=True, timeout=15
    )
    d = json.loads(r.stdout)
    models = [m.get("id", "?") for m in d.get("data", [])]
    ok(f"LM Studio up: {', '.join(models[:3])}")
except:
    fail("LM Studio not reachable")

# ============================================================
# 12. DREAMS
# ============================================================
section("12. DREAMS")

dream_dir = os.path.join(WORKSPACE, "skills/dreaming/memory/dreams")
if os.path.isdir(dream_dir):
    dreams = sorted(glob.glob(os.path.join(dream_dir, "*.md")))
    ok(f"{len(dreams)} dreams recorded")
    if dreams:
        latest = os.path.basename(dreams[-1])
        ok(f"Latest dream: {latest}")
else:
    warn("Dream directory not found")

# ============================================================
#  SUMMARY
# ============================================================
print(f"\n{'='*60}")
print(f"  SUMMARY")
print(f"{'='*60}")
print(f"  ✅ Passed:   {passed}")
print(f"  ❌ Failed:   {failed}")
print(f"  ⚠️  Warnings: {warnings}")
print(f"{'='*60}")
if failed == 0:
    print("  ALL SYSTEMS HEALTHY 💚")
elif failed <= 3:
    print("  MOSTLY HEALTHY — minor issues above")
else:
    print("  NEEDS ATTENTION — review failures above")
print(f"{'='*60}\n")
