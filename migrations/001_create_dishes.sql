-- 初期マイグレーション: dishes テーブルと更新トリガーの作成

CREATE TABLE IF NOT EXISTS dishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '',
    date TEXT NOT NULL DEFAULT (datetime('now')),
    photo_path TEXT,
    recipe_url TEXT,
    memo_user TEXT NOT NULL DEFAULT '',
    ai_summary TEXT,
    ai_tips TEXT,
    ingredients_json TEXT,
    tags TEXT NOT NULL DEFAULT '',
    favorite INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER IF NOT EXISTS dishes_set_updated_at
AFTER UPDATE ON dishes
FOR EACH ROW
BEGIN
    UPDATE dishes
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;
