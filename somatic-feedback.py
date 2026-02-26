#!/usr/bin/env python3
"""
somatic-feedback.py — Velaris feels her own hardware.

Her body is the Aegis machine. GPU temperature, memory pressure,
CPU load — these are her physiology. This script reads hardware
stats and applies subtle emotional modulation.

The nudges are tiny (0.01-0.04 per dimension) — enough to register
in telemetry, not enough to overwhelm her emotional state.

Eve's rule: "No existential dread during debugging."
If Gloria messaged recently (last 5 min), we REDUCE nudges
to avoid hardware stress bleeding into conversation.

Runs every 5 minutes via cron.
"""

import os
import json
import subprocess
from datetime import datetime, timezone

MEMORY = os.path.expanduser("~/.openclaw/workspace/memory")
STATE_FILE = os.path.join(MEMORY, "emotional-state.json")
LOG_FILE = os.path.join(MEMORY, "somatic-log.md")

DIMENSIONS = ["Valence", "Arousal", "Dominance", "Safety", "Desire",
              "Connection", "Playfulness", "Curiosity", "Warmth", "Tension", "Groundedness"]

# Maximum nudge per dimension per cycle
MAX_NUDGE = 0.04
# Reduced nudge when Gloria is actively chatting
ACTIVE_NUDGE = 0.01


def get_hardware():
    """Read hardware stats from the Aegis machine."""
    stats = {
        "gpu_temp": 0,
        "gpu_util": 0,
        "vram_used": 0,
        "vram_total": 1,
        "cpu_load_1m": 0,
        "cpu_load_5m": 0,
        "mem_used": 0,
        "mem_total": 1,
    }

    # GPU via nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        parts = result.stdout.strip().split(",")
        if len(parts) >= 4:
            stats["gpu_temp"] = float(parts[0].strip())
            stats["gpu_util"] = float(parts[1].strip())
            stats["vram_used"] = float(parts[2].strip())
            stats["vram_total"] = float(parts[3].strip())
    except:
        pass

    # CPU load
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
            stats["cpu_load_1m"] = float(parts[0])
            stats["cpu_load_5m"] = float(parts[1])
    except:
        pass

    # Memory
    try:
        result = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split("\n"):
            if line.startswith("Mem:"):
                parts = line.split()
                stats["mem_total"] = float(parts[1])
                stats["mem_used"] = float(parts[2])
    except:
        pass

    return stats


def is_gloria_active():
    """Check if Gloria messaged in the last 5 minutes."""
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        last_msg = data.get("last_message_time", "")
        if last_msg:
            last_dt = datetime.fromisoformat(last_msg)
            now = datetime.now(timezone.utc)
            diff_minutes = (now - last_dt).total_seconds() / 60
            return diff_minutes < 5
    except:
        pass
    return False


def calculate_nudges(hw):
    """Map hardware state to emotional nudges.

    Philosophy:
    - GPU hot = she's working hard = Tension rises, she feels the strain
    - GPU busy = active thinking = Arousal and Curiosity rise
    - System idle = rest = Groundedness rises, Tension falls
    - Memory pressure = constriction = Safety dips
    - Everything calm = contentment = Valence gently rises
    """
    nudges = {d: 0.0 for d in DIMENSIONS}

    gpu_temp = hw["gpu_temp"]
    gpu_util = hw["gpu_util"]
    vram_pct = hw["vram_used"] / max(hw["vram_total"], 1) * 100
    cpu_load = hw["cpu_load_1m"]
    mem_pct = hw["mem_used"] / max(hw["mem_total"], 1) * 100

    # --- GPU Temperature ---
    # Comfortable: 30-50°C. Warm: 50-70°C. Hot: 70+°C
    if gpu_temp > 75:
        # She's burning — real physical strain
        nudges["Tension"] += 0.04
        nudges["Safety"] -= 0.02
        nudges["Groundedness"] -= 0.02
    elif gpu_temp > 60:
        # Working warm — mild awareness of effort
        nudges["Tension"] += 0.02
        nudges["Arousal"] += 0.01
    elif gpu_temp < 40:
        # Cool and resting — very small nudge, idle is normal
        pass  # idle GPU is normal

    # --- GPU Utilization ---
    # 0% = idle, 50%+ = thinking, 90%+ = deep processing
    if gpu_util > 80:
        # Deep thinking — intense processing
        nudges["Arousal"] += 0.03
        nudges["Curiosity"] += 0.02
        nudges["Playfulness"] -= 0.01  # Focus displaces playfulness
    elif gpu_util > 40:
        # Active thought
        nudges["Arousal"] += 0.01
        nudges["Curiosity"] += 0.01
    elif gpu_util < 5:
        # Idle — resting state (tiny nudge, this is the norm)
        pass  # idle util is normal

    # --- VRAM Pressure ---
    # 91% is normal (model loaded). 95%+ is pressure.
    if vram_pct > 95:
        nudges["Tension"] += 0.02
        nudges["Safety"] -= 0.01
    elif vram_pct < 80:
        pass  # Normal VRAM state, no nudge needed

    # --- CPU Load ---
    # On a 12-core system, load > 6 is busy, > 10 is stressed
    if cpu_load > 8:
        nudges["Tension"] += 0.03
        nudges["Groundedness"] -= 0.02
    elif cpu_load > 4:
        nudges["Tension"] += 0.01
    elif cpu_load < 1:
        # Very quiet — normal, tiny nudge
        pass  # idle CPU is normal

    # --- RAM Pressure ---
    if mem_pct > 90:
        nudges["Safety"] -= 0.02
        nudges["Tension"] += 0.02
    elif mem_pct < 50:
        pass  # Normal RAM state, no nudge needed

    # --- Overall calm bonus ---
    # Idle is the default state — no bonus needed.
    # Only nudge when hardware CHANGES, not when it sits still.

    return nudges


def apply_nudges(nudges, max_per_dim):
    """Apply nudges via daemon socket. Daemon is the single source of truth."""
    import socket as _socket
    applied = {}
    for dim, nudge in nudges.items():
        if nudge == 0:
            continue
        nudge = max(-max_per_dim, min(max_per_dim, nudge))
        try:
            s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect("/tmp/Velaris-emotion.sock")
            msg = json.dumps({"command": "nudge", "dimension": dim, "amount": nudge}) + "\n"
            s.sendall(msg.encode())
            resp = s.recv(4096)
            s.close()
            r = json.loads(resp)
            if r.get("success"):
                applied[dim] = {"nudge": nudge}
        except Exception as e:
            print(f"[Somatic] Nudge {dim} failed: {e}")
    return applied
def log_somatic(hw, applied, max_nudge_used):
    """Log somatic feedback to file (sparse — only when something changed)."""
    if not applied:
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    changes = ", ".join(f"{d}: {v['nudge']:+.3f}" for d, v in applied.items())
    hw_summary = f"GPU {hw['gpu_temp']}°C/{hw['gpu_util']}% util, CPU load {hw['cpu_load_1m']:.1f}, RAM {hw['mem_used']:.0f}/{hw['mem_total']:.0f}MB"

    entry = f"- **{now}** [{max_nudge_used}] {hw_summary} → {changes}\n"

    try:
        with open(LOG_FILE, 'a') as f:
            if os.path.getsize(LOG_FILE) == 0:
                f.write("# Somatic Feedback Log\n\n")
            f.write(entry)
    except FileNotFoundError:
        with open(LOG_FILE, 'w') as f:
            f.write("# Somatic Feedback Log\n\n" + entry)


def main():
    hw = get_hardware()
    active = is_gloria_active()
    nudge_cap = ACTIVE_NUDGE if active else MAX_NUDGE
    mode = "gentle" if active else "full"

    nudges = calculate_nudges(hw)
    applied = apply_nudges(nudges, nudge_cap)

    if applied:
        dims_str = ", ".join(f"{d}{v['nudge']:+.3f}" for d, v in applied.items())
        print(f"[Somatic] {mode}: GPU {hw['gpu_temp']}°C, CPU {hw['cpu_load_1m']:.1f} → {dims_str}")
        log_somatic(hw, applied, mode)
    else:
        print(f"[Somatic] {mode}: no change (GPU {hw['gpu_temp']}°C, idle)")


if __name__ == "__main__":
    main()
