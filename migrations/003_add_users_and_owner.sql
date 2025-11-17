-- v0.3: ユーザーテーブルと dishes.owner_id を追加

-- users テーブルを作成
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- dishes に owner_id カラムを追加するため、create-copy-replace パターンで再作成
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS dishes_new (
    id INTEGER PRIMARY KEY,
    name TEXT,
    date TEXT,
    photo_path TEXT,
    recipe_url TEXT,
    memo_user TEXT,
    ai_summary TEXT,
    ai_tips TEXT,
    ingredients_json TEXT,
    tags TEXT,
    favorite INTEGER DEFAULT 0,
    is_public INTEGER DEFAULT 0,
    owner_id INTEGER DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- データを移行（新しいカラムは NULL で埋める）
INSERT INTO dishes_new (id, name, date, photo_path, recipe_url, memo_user, ai_summary, ai_tips, ingredients_json, tags, favorite, is_public, created_at, updated_at)
SELECT id, name, date, photo_path, recipe_url, memo_user, ai_summary, ai_tips, ingredients_json, tags, favorite, is_public, created_at, updated_at
FROM dishes;

DROP TABLE dishes;
ALTER TABLE dishes_new RENAME TO dishes;

-- トリガーを再作成
DROP TRIGGER IF EXISTS dishes_set_updated_at;
CREATE TRIGGER dishes_set_updated_at
AFTER UPDATE ON dishes
FOR EACH ROW
BEGIN
    UPDATE dishes SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

-- インデックスを追加
CREATE INDEX IF NOT EXISTS idx_dishes_owner_id ON dishes (owner_id);

COMMIT;
