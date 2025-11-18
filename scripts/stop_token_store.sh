#!/usr/bin/env bash
set -euo pipefail
PIDFILE="/workspaces/CoCock_app/.token_store.pid"
if [ ! -f "$PIDFILE" ]; then
  echo "No token_store pidfile found"
  exit 0
fi
PID=$(cat "$PIDFILE" 2>/dev/null || true)
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  echo "Stopping token_store pid $PID"
  kill "$PID"
  sleep 0.5
  if kill -0 "$PID" 2>/dev/null; then
    echo "Force kill $PID"
    kill -9 "$PID" || true
  fi
fi
rm -f "$PIDFILE"
echo "token_store stopped"
