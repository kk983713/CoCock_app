-- v0.4: 匿名編集用トークンと投稿者表示名を追加

ALTER TABLE dishes ADD COLUMN author_display_name TEXT;
ALTER TABLE dishes ADD COLUMN edit_token TEXT;
ALTER TABLE dishes ADD COLUMN edit_token_created_at TEXT;
