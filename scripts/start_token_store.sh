#!/usr/bin/env bash
set -euo pipefail
PIDFILE="/workspaces/CoCock_app/.token_store.pid"
LOGFILE="/workspaces/CoCock_app/token_store.log"
if [ -f "$PIDFILE" ]; then
  PID=$(cat "$PIDFILE" 2>/dev/null || true)
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "token_store already running (pid $PID)"
    exit 0
  else
    echo "Stale pidfile found, removing"
    rm -f "$PIDFILE"
  fi
fi
echo "Starting token_store on 0.0.0.0:8765..."
# Use unbuffered mode so prints appear in the logfile immediately
nohup python3 -u scripts/token_store.py --host 0.0.0.0 --port 8765 > "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "token_store started with pid $(cat $PIDFILE), log: $LOGFILE"
