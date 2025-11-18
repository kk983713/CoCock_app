#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -x "$ROOT/.venv/bin/python" ]; then
  VENV_PY="$ROOT/.venv/bin/python"
else
  # Debug info: print PATH and python detection results to help CI troubleshooting
  echo "DEBUG: PATH=$PATH"
  echo "DEBUG: command -v python -> $(command -v python || true)"
  echo "DEBUG: command -v python3 -> $(command -v python3 || true)"
  echo "DEBUG: which python -> $(which python 2>/dev/null || true)"
  echo "DEBUG: which python3 -> $(which python3 2>/dev/null || true)"

  # Fallback to system python in CI where a virtualenv may not exist
  VENV_PY="$(command -v python || command -v python3 || command -v python3.11 || true)"
fi

if [ -z "$VENV_PY" ]; then
  echo "ERROR: No python executable found (expected .venv or system python). PATH=$PATH" >&2
  exit 100
else
  echo "Using python executable: $VENV_PY"
fi

echo "1) Initialize DB and seed test user"
$VENV_PY $ROOT/scripts/test_db_init.py

echo "2) Start Streamlit"
STARTED_STREAMLIT=false
# If streamlit is already running (pidfile exists and process alive), skip starting.
if [ -f "$ROOT/streamlit.pid" ]; then
  PID_EXISTING=$(cat "$ROOT/streamlit.pid" || true)
  if [ -n "$PID_EXISTING" ] && kill -0 "$PID_EXISTING" 2>/dev/null; then
    echo "Streamlit already running with PID $PID_EXISTING; skipping start."
  else
    echo "Found stale pidfile or process not running; starting Streamlit."
    $ROOT/scripts/start_streamlit.sh
    STARTED_STREAMLIT=true
    sleep 3
  fi
else
  # also check if something is listening on 8501 (maybe started outside pidfile)
  if nc -z 127.0.0.1 8501 2>/dev/null; then
    echo "Port 8501 already in use; assuming Streamlit running."
  else
    echo "No streamlit pidfile and port free; starting Streamlit."
    $ROOT/scripts/start_streamlit.sh
    STARTED_STREAMLIT=true
    sleep 3
  fi
fi

EXIT_CODE=0

echo "3) Run E2E scripts (both, collect exit codes)"
$VENV_PY $ROOT/tests/e2e/e2e_register_post.py || true
RC1=$?
$VENV_PY $ROOT/tests/e2e/e2e_login_post.py || true
RC2=$?

echo "3b) Post-check: verify DB has a dish by test user"
# Run a small python check: look up user id and any dish owned by them
echo "3b) Post-check: verify DB has a dish by test user (retry up to 10s)"
PYRC=3
for i in $(seq 1 10); do
  $VENV_PY $ROOT/tests/e2e/_db_check.py || true
  PYRC=$?
  if [ $PYRC -eq 0 ]; then
    break
  fi
  sleep 1
done

$ROOT/scripts/stop_streamlit.sh || true
echo "3c) Collect artifacts for upload"
ARTDIR="$ROOT/tests/e2e/artifacts"
mkdir -p "$ARTDIR"

# list of legacy artifacts at repo root to collect if present
LEGACY_FILES=(
  "$ROOT/e2e_page_content.html"
  "$ROOT/e2e_page_content2.html"
  "$ROOT/e2e_after_register.png"
  "$ROOT/e2e_after_login.png"
  "$ROOT/e2e_after_submit.png"
  "$ROOT/e2e_after_submit2.png"
  "$ROOT/streamlit.log"
)

for f in "${LEGACY_FILES[@]}"; do
  if [ -f "$f" ]; then
    echo "Collecting $f -> $ARTDIR"
    mv "$f" "$ARTDIR/" || cp -a "$f" "$ARTDIR/" || true
  fi
done

# Also pick up anything under tests/e2e/artifacts already produced
if [ -d "$ROOT/tests/e2e/artifacts" ]; then
  echo "Ensuring artifacts directory exists: $ARTDIR"
  mkdir -p "$ARTDIR"
fi

echo "Artifacts present (root $ARTDIR):"
ls -alh "$ARTDIR" || echo "(no artifacts found)"

echo "4) Stop Streamlit"
if [ "$STARTED_STREAMLIT" = true ]; then
  echo "Stopping Streamlit started by this script"
  $ROOT/scripts/stop_streamlit.sh || true
else
  echo "Not stopping Streamlit because this script did not start it"
fi
if [ "$STARTED_STREAMLIT" = true ]; then
  echo "Stopping Streamlit started by this script"
  $ROOT/scripts/stop_streamlit.sh || true
else
  echo "Not stopping Streamlit because this script did not start it"
fi

if [ $PYRC -eq 0 ]; then
  echo "E2E overall: SUCCESS (DB confirmed)"
  exit 0
else
  echo "E2E overall: FAILURE (DB check rc=$PYRC). Individual RCs: reg=$RC1 login=$RC2"
  exit 1
fi
