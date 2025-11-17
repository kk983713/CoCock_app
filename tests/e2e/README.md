E2E tests for CoCock_app

Overview
- This folder contains Playwright-based E2E scripts used during development and CI.
- The scripts currently run headless and rely on the local Streamlit server and the local SQLite DB `receipts.db`.

Quick run (local, using the project's venv)

1. Ensure the project's virtualenv is activated, or run with the full path to the venv python:

   /workspaces/CoCock_app/.venv/bin/python /workspaces/CoCock_app/tests/run_e2e.sh

What `tests/run_e2e.sh` does
- Recreates `receipts.db` from migrations and seeds a test user (`scripts/test_db_init.py`)
- Starts Streamlit (background)
- Runs the E2E scripts `e2e_register_post.py` and `e2e_login_post.py`
- Stops Streamlit and returns a non-zero exit code on failure

CI notes
- In CI, create and activate the venv, install dependencies from `requirements.txt`, then run `tests/run_e2e.sh`.
- Make sure the CI runner has network and process permissions required to run Playwright; Playwright browser binaries may need to be installed in CI or cached.
