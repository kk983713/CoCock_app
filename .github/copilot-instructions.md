# CoCock_app AI Agent Instructions

このリポジトリは Streamlit ベースのレシピ・写真ログアプリケーションです。以下の構造と規約を理解してコード変更を行ってください。

## アーキテクチャ概要

- **アプリケーション構造**:
  - `streamlit_app.py`: メインのStreamlitアプリケーション（UI定義）
  - `db.py`: SQLiteマイグレーション管理
  - `storage.py`: 写真ファイル保存のユーティリティ
  - `migrations/*.sql`: SQLiteスキーマ定義

## データフロー

1. **画像保存**: 
   - 写真は `data/dishes/<dish_id>/cover.<ext>` に保存
   - `storage.py::build_dish_photo_path()` で保存パスを生成

2. **データベース**:
   - SQLite (`receipts.db`) でデータを永続化
   - `dishes` テーブルが料理情報を保持
   - スキーマ変更は `migrations/` 配下に連番SQLで追加

## 開発ワークフロー

```bash
# データベース初期化
python db.py

# 開発サーバー起動（ポート8501で自動転送）
streamlit run streamlit_app.py
```

## プロジェクト固有の規約

1. **環境管理**:
   - VS Code Dev Container で開発環境を統一
   - 秘密情報は `.env` で管理（`.env.example` 参照）

2. **データ永続化**:
   - `receipts.db` と `data/` は Git 管理対象外
   - 会話ログ (`conversation_log.md`) はバージョン管理対象

3. **コード規約**:
   - Python 3.11+ の型ヒントを活用
   - SQLite操作は生SQLで記述（ORMなし）

## 参考実装

- フォーム入力: `streamlit_app.py` の `dish_entry_form`
- ファイル保存: `storage.py` の `build_dish_photo_path()`
- DBマイグレーション: `migrations/001_create_dishes.sql`