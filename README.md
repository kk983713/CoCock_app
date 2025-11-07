# CoCock_app

簡易レシピ・写真ログを Streamlit で動かすプロトタイプです。Windows/WSL と macOS のどちらでも同じ開発体験になるよう、VS Code Dev Container と Git で管理します。

## 開発環境 (Dev Container)
1. VS Code に [Dev Containers 拡張機能](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) を入れる。
2. このリポジトリを `F:\\pythonkei\\CoCock_app` (もしくは `/mnt/f/pythonkei/CoCock_app`) に配置し、VS Code で開く。
3. コマンドパレットで「Dev Containers: Reopen in Container」を実行。
4. コンテナ起動後、自動で `requirements.txt` がインストールされ、Python 3.11 + Streamlit + OCR/PDF 用ツール (tesseract-ocr, poppler-utils, libgl1) が整います。
5. Streamlit を起動する場合は `streamlit run streamlit_app.py --server.port 8501` を実行。ポート 8501 は `devcontainer.json` で転送済みです。

## .env と秘密情報
- `cp .env.example .env` でローカル用ファイルを作り、API キーなどを追記してください。
- `.env` や `.env.local` など秘密情報は `.gitignore` で除外されるため、Git に載りません。

## データ・バイナリの扱い
- SQLite (`receipts.db`) と写真保存用 `data/` 配下は Git から除外しています。必要なら `.gitkeep` だけが空ディレクトリを保持します。
- 会話ログ `conversation_log.md` はテキストとして Git で追跡します。更新したら通常のファイルと同様にコミットしてください。

## 便利コマンド
```bash
# マイグレーション適用 (データベースを初期化)
python db.py

# Streamlit 開発サーバー
streamlit run streamlit_app.py
```

## 開発ロードマップ
### 現状できていること
- Dev Container・requirements・マイグレーション適用ユーティリティまで整備済み
- `streamlit_app.py` で写真 / 料理名 / URL / メモを登録でき、`data/` に画像を保存
- 会話ログや仕様メモ (`recipe_log_mvp_spec.md`) で決定事項を追える状態

### 直近 TODO (v0.1)
1. Streamlit のサイドページかタブで「登録済みの料理一覧」を表示し、写真やメモをすぐ確認できるようにする
2. 入力フォームに最低限のバリデーション（料理名かメモのどちらか必須など）とエラーメッセージを追加
3. README に記載した手順どおりに `streamlit run` → 登録 → DB 確認の手動テストを行い、必要なら手順を追記

### 先のアイデア (v0.2 以降)
- タグ・お気に入りフラグ・検索フィルタの UI を追加する
- AI 要約（materials / steps / tips）を生成し `dishes` テーブルの該当カラムへ保存
- requirements のロックファイル導入や pytest / lint の CI 整備
- 連携 API 用のクレデンシャル管理を `.env` フローに統一
