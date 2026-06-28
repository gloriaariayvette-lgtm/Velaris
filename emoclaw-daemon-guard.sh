#!/usr/bin/env bash
# emoclaw-daemon-guard.sh — Restarts heartbeat if it dies. Runs every 5 min.
bash "$(dirname "$0")/emoclaw-heartbeat.sh"
