-- 005_add_submission_attempts.sql
-- 軽量なスパム防止・監査用テーブル：投稿試行を記録する
CREATE TABLE IF NOT EXISTS submission_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_display_name TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_submission_attempts_author_created_at ON submission_attempts(author_display_name, created_at);
