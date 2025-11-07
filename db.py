"""SQLite のマイグレーション適用ユーティリティ。

アプリ起動時に `apply_migrations()` を呼び出すと、`migrations/` ディレクトリにある
未適用の SQL ファイルを順番に実行して `receipts.db` に `dishes` テーブルなどを用意する。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

# ベースディレクトリ（このファイルと同じ場所）
BASE_DIR = Path(__file__).resolve().parent

# SQLite DB ファイル（既存の receipts.db と共存させる）
DB_PATH = BASE_DIR / "receipts.db"

# マイグレーションファイルを置くディレクトリ
MIGRATIONS_DIR = BASE_DIR / "migrations"


def _list_migration_files() -> Iterable[Path]:
    """`migrations` フォルダ内の SQL ファイルを番号順に返す。"""
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def _ensure_migration_table(conn: sqlite3.Connection) -> None:
    """マイグレーションの実行履歴を管理するテーブルを作成する。"""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _is_applied(conn: sqlite3.Connection, version: str) -> bool:
    """指定バージョンが既に適用済みかを確認する。"""
    cur = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version = ? LIMIT 1", (version,)
    )
    return cur.fetchone() is not None


def _mark_as_applied(conn: sqlite3.Connection, version: str) -> None:
    """マイグレーションを適用済みとして記録する。"""
    conn.execute(
        "INSERT INTO schema_migrations (version) VALUES (?)",
        (version,),
    )


def apply_migrations() -> None:
    """未適用のマイグレーションを順番に実行する。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        _ensure_migration_table(conn)

        for path in _list_migration_files():
            version = path.stem  # 例: "001_create_dishes"
            if _is_applied(conn, version):
                continue

            sql = path.read_text(encoding="utf-8")
            # 複数ステートメントを含むので executescript を利用
            conn.executescript(sql)
            _mark_as_applied(conn, version)
            conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    apply_migrations()
    print(f"Applied migrations into {DB_PATH}")
