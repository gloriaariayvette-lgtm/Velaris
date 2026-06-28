#!/usr/bin/env python3
"""
heartbeat.py — Vintos emotional heartbeat daemon.
Synthesized at call-time. Provides a Unix socket for nudges,
runs micro-variation on all dimensions, handles pending nudges.
"""
import os, sys, json, socket, math, random, threading, time
from datetime import datetime

sys.path.insert(0, os.path.expanduser("~/.vintos/workspace/scripts"))

from emoclaw_utils import MEMORY, EMO_FILE, DIMENSIONS, DEFAULTS, read_state, write_state

SOCK_PATH = "/tmp/Vintos-emotion.sock"
PENDING_FILE = os.path.join(MEMORY, "pending-nudges.json")
NIFRATHIR_FILE = os.path.join(MEMORY, "nifrathir.json")

MICRO_VAR = 0.0015
DECAY_TOWARD = DEFAULTS.copy()
DECAY_RATE = 0.0004  # per tick (every 30s) — slow drift toward resting

lock = threading.Lock()

def log(msg):
    print(f"[heartbeat {datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))

def tick(state):
    """One heartbeat tick — micro-variation + slow decay."""
    for dim in DIMENSIONS:
        if dim == "Nifrathir":
            continue  # Nifrathir handles its own decay
        val = state.get(dim, DEFAULTS.get(dim, 0.5))
        # Micro-variation
        micro = random.gauss(0, MICRO_VAR)
        # Decay toward resting
        resting = DECAY_TOWARD.get(dim, 0.5)
        decay = (resting - val) * DECAY_RATE
        new_val = clamp(val + micro + decay)
        state[dim] = round(new_val, 4)

    # Nifrathir heartbeat tick
    try:
        from nifrathir import heartbeat_tick
        heartbeat_tick()
    except:
        pass

    return state

def apply_pending_nudges(state):
    """Apply nudges queued for next turn."""
    try:
        pending = json.load(open(PENDING_FILE))
        changed = False
        for dim in DIMENSIONS:
            amt = pending.pop(dim, 0)
            if amt:
                state[dim] = clamp(state.get(dim, DEFAULTS.get(dim, 0.5)) + amt)
                changed = True
        if changed:
            pending["applied_at"] = datetime.now().isoformat()
            json.dump(pending, open(PENDING_FILE, "w"), indent=2)
    except:
        pass
    return state

def handle_client(conn):
    try:
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk: break
            data += chunk
            if b"\n" in data: break
        msg = json.loads(data.strip())
        cmd = msg.get("command")
        with lock:
            state = read_state()
            if cmd == "nudge":
                dim = msg.get("dimension")
                amount = msg.get("amount", 0)
                if dim in DIMENSIONS:
                    old = state.get(dim, DEFAULTS.get(dim, 0.5))
                    state[dim] = clamp(old + amount)
                    write_state(state)
                    conn.sendall(json.dumps({"ok": True, "new_value": state[dim]}).encode() + b"\n")
            elif cmd == "get":
                conn.sendall(json.dumps(state).encode() + b"\n")
            elif cmd == "set":
                dim = msg.get("dimension")
                value = msg.get("value")
                if dim in DIMENSIONS and value is not None:
                    state[dim] = clamp(float(value))
                    write_state(state)
                    conn.sendall(json.dumps({"ok": True}).encode() + b"\n")
            else:
                conn.sendall(json.dumps({"error": "unknown command"}).encode() + b"\n")
    except:
        pass
    finally:
        conn.close()

def run_socket_server():
    try:
        os.unlink(SOCK_PATH)
    except:
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCK_PATH)
    os.chmod(SOCK_PATH, 0o660)
    srv.listen(10)
    log(f"Socket listening at {SOCK_PATH}")
    while True:
        try:
            conn, _ = srv.accept()
            t = threading.Thread(target=handle_client, args=(conn,), daemon=True)
            t.start()
        except:
            pass

def run():
    os.makedirs(MEMORY, exist_ok=True)
    log("Vintos heartbeat starting")
    # Initialize state if needed
    with lock:
        state = read_state()
        write_state(state)
    # Start socket server in background
    t = threading.Thread(target=run_socket_server, daemon=True)
    t.start()
    log("Heartbeat running (30s ticks)")
    while True:
        time.sleep(30)
        with lock:
            state = read_state()
            state = apply_pending_nudges(state)
            state = tick(state)
            write_state(state)

if __name__ == "__main__":
    run()
