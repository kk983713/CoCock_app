-- v0.6: Add password_hash and email to users

PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

-- If users table exists, add columns
CREATE TABLE IF NOT EXISTS users_new (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    email TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users_new (id, username, created_at)
SELECT id, username, created_at FROM users;

DROP TABLE IF EXISTS users;
ALTER TABLE users_new RENAME TO users;

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

COMMIT;
PRAGMA foreign_keys=on;
