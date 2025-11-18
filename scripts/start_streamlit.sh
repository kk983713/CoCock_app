#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
VENVDIR="$ROOT_DIR/.venv"
# prefer venv python when present, otherwise fall back to system python
if [ -x "$VENVDIR/bin/python" ]; then
	PY="$VENVDIR/bin/python"
else
	PY="$(command -v python || command -v python3 || command -v python3.11 || true)"
fi
LOG="$ROOT_DIR/streamlit.log"
PIDFILE="$ROOT_DIR/streamlit.pid"

echo "Starting Streamlit..."
if [ -z "$PY" ]; then
	echo "ERROR: no python executable found (looked for $VENVDIR/bin/python then system python)." >&2
	echo "Ensure python is installed or create a .venv with the project dependencies." >&2
	exit 1
fi
nohup "$PY" -m streamlit run "$ROOT_DIR/streamlit_app.py" --server.port 8501 --server.address 0.0.0.0 > "$LOG" 2>&1 &
echo $! > "$PIDFILE"
echo "Started PID $(cat "$PIDFILE") - logs: $LOG (using python: $PY)"
