-- v0.2: 検索・ソートに使う主要カラムへインデックスを追加

CREATE INDEX IF NOT EXISTS idx_dishes_name
    ON dishes (name);

CREATE INDEX IF NOT EXISTS idx_dishes_memo_user
    ON dishes (memo_user);

CREATE INDEX IF NOT EXISTS idx_dishes_tags
    ON dishes (tags);

CREATE INDEX IF NOT EXISTS idx_dishes_favorite
    ON dishes (favorite);

CREATE INDEX IF NOT EXISTS idx_dishes_created_at
    ON dishes (created_at);
