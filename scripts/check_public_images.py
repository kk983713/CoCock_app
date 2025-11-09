#!/usr/bin/env python3
"""Check public dish images and write missing.json.

Exits with code 1 if missing images are found.
"""
import json
import pathlib
import sqlite3
import sys


def main() -> int:
    db = pathlib.Path('receipts.db')
    missing = []
    if db.exists():
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, photo_path FROM dishes WHERE is_public=1")
            for id_, p in cur.fetchall():
                if not p:
                    continue
                if not pathlib.Path(p).exists():
                    missing.append({'id': id_, 'path': p})
        except Exception as e:
            print('DB error', e)
        finally:
            conn.close()
    else:
        print('receipts.db not found; skipping image checks')

    open('missing.json', 'w').write(json.dumps(missing))
    print(json.dumps(missing))
    if missing:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
