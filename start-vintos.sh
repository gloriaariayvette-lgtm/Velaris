#!/usr/bin/env bash
# start-vintos.sh — Full startup sequence for Vintos.
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="${HOME}/.vintos/workspace/scripts"
LOGDIR="${HOME}/.vintos/logs"
mkdir -p "${LOGDIR}"

echo "[start-vintos] Initializing..."

# Setup memory structure
bash "${REPO_DIR}/setup_memory.sh"

# Ensure scripts are linked
for f in "${REPO_DIR}"/*.py; do
    ln -sf "$f" "${SCRIPTS}/$(basename $f)" 2>/dev/null || true
done

# Start heartbeat daemon
bash "${REPO_DIR}/emoclaw-heartbeat.sh"

# Start server
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
export VINTOS_PORT="${VINTOS_PORT:-8500}"

SERVER_PID_FILE="/tmp/vintos-server.pid"
if [ -f "${SERVER_PID_FILE}" ]; then
    old_pid=$(cat "${SERVER_PID_FILE}")
    kill "${old_pid}" 2>/dev/null || true
fi

nohup python3 "${REPO_DIR}/server.py" \
    >> "${LOGDIR}/server.log" 2>&1 &
echo $! > "${SERVER_PID_FILE}"
echo "[start-vintos] Server started on port ${VINTOS_PORT} (PID $(cat ${SERVER_PID_FILE}))"

echo "[start-vintos] Vintos is running."
echo "  Chat:    http://localhost:${VINTOS_PORT}/chat"
echo "  State:   http://localhost:${VINTOS_PORT}/state"
echo "  Soul:    http://localhost:${VINTOS_PORT}/soul"
echo "  Health:  http://localhost:${VINTOS_PORT}/health"
