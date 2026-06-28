#!/usr/bin/env bash
# emoclaw-heartbeat.sh — Ensures heartbeat daemon is running.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
PID_FILE="/tmp/vintos-heartbeat.pid"

is_running() {
    if [ -f "${PID_FILE}" ]; then
        pid=$(cat "${PID_FILE}")
        kill -0 "${pid}" 2>/dev/null && return 0
    fi
    return 1
}

if is_running; then
    exit 0
fi

export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
nohup python3 "${SCRIPTS}/heartbeat.py" >> "${HOME}/.vintos/logs/heartbeat.log" 2>&1 &
echo $! > "${PID_FILE}"
echo "[emoclaw-heartbeat] Started PID $(cat ${PID_FILE})"
