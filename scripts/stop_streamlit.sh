#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
PIDFILE="$ROOT_DIR/streamlit.pid"

if [ ! -f "$PIDFILE" ]; then
  echo "No pidfile found at $PIDFILE"
  exit 0
fi

PID=$(cat "$PIDFILE")
echo "Stopping Streamlit PID $PID"
kill "$PID" || true
rm -f "$PIDFILE"
echo "Stopped"
