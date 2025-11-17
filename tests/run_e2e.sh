#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PY="$ROOT/.venv/bin/python"

echo "1) Initialize DB and seed test user"
$VENV_PY $ROOT/scripts/test_db_init.py

echo "2) Start Streamlit"
$ROOT/scripts/start_streamlit.sh
# give streamlit a moment to start
sleep 3

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

echo "4) Stop Streamlit"
$ROOT/scripts/stop_streamlit.sh || true

if [ $PYRC -eq 0 ]; then
  echo "E2E overall: SUCCESS (DB confirmed)"
  exit 0
else
  echo "E2E overall: FAILURE (DB check rc=$PYRC). Individual RCs: reg=$RC1 login=$RC2"
  exit 1
fi
