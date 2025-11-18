#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
"$ROOT_DIR/scripts/stop_streamlit.sh" || true
sleep 1
"$ROOT_DIR/scripts/start_streamlit.sh"
