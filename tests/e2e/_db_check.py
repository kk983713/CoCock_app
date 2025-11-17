#!/usr/bin/env python3
import sqlite3
import sys

db='/workspaces/CoCock_app/receipts.db'
try:
    conn=sqlite3.connect(db)
    cur=conn.cursor()
    # Accept any dish whose name starts with 'E2E' AND was created recently
    # Use a 5-minute window to avoid matching old test data.
    cur.execute("SELECT id, name, owner_id, created_at FROM dishes WHERE name LIKE 'E2E%' AND datetime(created_at) >= datetime('now', '-5 minutes') ORDER BY id DESC LIMIT 1")
    d=cur.fetchone()
    if d:
        print('FOUND_DISH', d)
        sys.exit(0)
    else:
        print('NO_DISH')
        sys.exit(3)
except Exception as e:
    print('DBCHECK_ERROR', e)
    sys.exit(4)
