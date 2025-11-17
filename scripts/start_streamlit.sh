#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
VENVDIR="$ROOT_DIR/.venv"
PY="$VENVDIR/bin/python"
LOG="$ROOT_DIR/streamlit.log"
PIDFILE="$ROOT_DIR/streamlit.pid"

echo "Starting Streamlit..."
nohup "$PY" -m streamlit run "$ROOT_DIR/streamlit_app.py" --server.port 8501 --server.address 0.0.0.0 > "$LOG" 2>&1 &
echo $! > "$PIDFILE"
echo "Started PID $(cat "$PIDFILE") - logs: $LOG"
