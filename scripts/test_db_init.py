#!/usr/bin/env python3
"""
CI / local helper: recreate receipts.db from migrations and create a test user.
Usage: python scripts/test_db_init.py
"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "receipts.db"

# Test user credentials (match E2E scripts)
TEST_USER = "e2e_user"
TEST_PASS = "e2e_pass_123"
TEST_EMAIL = "e2e@example.test"

# Use passlib.pbkdf2_sha256 to hash the password (same as app PoC)
try:
    from passlib.hash import pbkdf2_sha256
except Exception:
    print("passlib not installed in environment. Please install requirements.txt in the venv.")
    sys.exit(1)


def run_db_py():
    """Run db.py to (re)create the schema/migrations if present."""
    print("Running db.py to (re)create DB schema...")
    env = os.environ.copy()
    # call the project's python
    cmd = [sys.executable, str(ROOT / "db.py")]
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print("db.py failed:", res.stderr)
        sys.exit(res.returncode)


def seed_test_user(db_path: str):
    print("Seeding test user into DB...", db_path)
    pw_hash = pbkdf2_sha256.hash(TEST_PASS)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Insert user row. If users table already has this username, delete it first.
    try:
        cur.execute("DELETE FROM users WHERE username = ?", (TEST_USER,))
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (TEST_USER, TEST_EMAIL, pw_hash),
        )
        conn.commit()
        print("created user", TEST_USER)
    except Exception as e:
        print("Error seeding user:", e)
        conn.rollback()
        conn.close()
        sys.exit(1)
    conn.close()


def main():
    if DB.exists():
        print("Removing existing DB:", DB)
        DB.unlink()

    run_db_py()

    if not DB.exists():
        print("Expected receipts.db at", DB, "but not found")
        sys.exit(2)

    seed_test_user(str(DB))
    print("DB initialization and seed complete.")


if __name__ == '__main__':
    main()
