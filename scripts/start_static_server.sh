#!/usr/bin/env bash
set -euo pipefail
PIDFILE="/workspaces/CoCock_app/.static_http.pid"
LOGFILE="/workspaces/CoCock_app/static_http.log"
PORT=8000
if [ -f "$PIDFILE" ]; then
  PID=$(cat "$PIDFILE" 2>/dev/null || true)
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "static http server already running (pid $PID)"
    exit 0
  else
    echo "Stale pidfile found, removing"
    rm -f "$PIDFILE"
  fi
fi
echo "Starting static http.server on 0.0.0.0:$PORT (serves project root)"
nohup python3 -m http.server "$PORT" > "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "static server started pid $(cat $PIDFILE), log: $LOGFILE"
