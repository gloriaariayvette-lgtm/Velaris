#!/bin/bash
# start-velaris.sh — Start all Velaris services

echo "[Velaris] Starting services..."

# EmoClaw daemon
bash ~/.openclaw/workspace/skills/emoclaw/scripts/daemon.sh start
sleep 3

# Emotion forwarder (real-time message → emotion pipeline)
if ! pgrep -f "emotion_forwarder.py" > /dev/null; then
    cd ~/.openclaw/workspace
    source emotion_model/.venv/bin/activate
    nohup python3 emotion_forwarder.py > /tmp/emotion-forwarder.log 2>&1 &
    echo "[✓] Emotion forwarder started (PID $!)"
else
    echo "[✓] Emotion forwarder already running"
fi

# Verify crons
crontab -l 2>/dev/null | grep -q "dream-trigger" && echo "[✓] Crons active" || echo "[!] Crons missing"

echo "[Velaris] All services started."
