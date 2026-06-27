#!/bin/bash
# Backup unfinished-threads.json before any destructive operation
THREADS="$HOME/.openclaw/workspace/memory/unfinished-threads.json"
BACKUP_DIR="$HOME/.openclaw/workspace/memory/threads-backup"
mkdir -p "$BACKUP_DIR"
[ -f "$THREADS" ] && cp "$THREADS" "$BACKUP_DIR/threads-$(date +%Y-%m-%d_%H%M%S).json"
# Keep last 20 backups
ls -t "$BACKUP_DIR"/threads-*.json 2>/dev/null | tail -n +21 | xargs rm -f 2>/dev/null
