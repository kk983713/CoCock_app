-- Add is_public column to dishes table. Create a new table and copy data to avoid ALTER TABLE errors.
BEGIN TRANSACTION;

-- Create a new table with the extra is_public column
CREATE TABLE IF NOT EXISTS dishes_new (
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
    is_public INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Copy existing data if any (map columns)
INSERT OR IGNORE INTO dishes_new (
    id, name, date, photo_path, recipe_url, memo_user, ai_summary, ai_tips, ingredients_json, tags, favorite, created_at, updated_at
)
SELECT
    id, name, date, photo_path, recipe_url, memo_user, ai_summary, ai_tips, ingredients_json, tags, favorite, created_at, updated_at
FROM dishes;

-- Replace old table
DROP TABLE IF EXISTS dishes;
ALTER TABLE dishes_new RENAME TO dishes;

-- Recreate trigger for updated_at
CREATE TRIGGER IF NOT EXISTS dishes_set_updated_at
AFTER UPDATE ON dishes
FOR EACH ROW
BEGIN
    UPDATE dishes
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

COMMIT;
