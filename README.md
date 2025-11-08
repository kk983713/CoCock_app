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

## v0.2 UI の使い方
1. `streamlit run streamlit_app.py` を実行し、ブラウザでタブが 2 つある画面を開く。
2. **登録フォーム** タブで写真 / 料理名 / URL / メモに加えて「タグ（カンマ区切り）」と「また作りたい（お気に入り）」を入力し、`登録する` を押す。
3. 登録が成功すると「一覧 / 検索」タブに自動反映される。タグが多い場合はボタン（チップ）をクリックすると同じタグでフィルタされる。
4. 一覧タブではキーワード・タグ・お気に入りフラグで即時絞り込みが可能。フィルタをクリアしたい場合は `フィルタをクリア` ボタンを利用する。
5. 各カード右下の「☆ / ★」ボタンでお気に入り状態をトグルでき、その結果は即座に保存される。

## 開発ロードマップ
### 現状できていること
- Dev Container・requirements・マイグレーション適用ユーティリティまで整備済み
- `streamlit_app.py` の v0.2 で写真 / 料理名 / URL / メモ / タグ / お気に入りを登録し、同画面の一覧タブで即検索・フィルタできる
- 会話ログや仕様メモ (`recipe_log_mvp_spec.md`) で決定事項を追える状態

### 直近 TODO (v0.2 仕上げ)
1. **入力フォームのバリデーション強化**  
   - 料理名 or メモのいずれかが空なら送信ボタンを無効化し、理由を日本語で表示。  
   - URL は `http://` / `https://` から始まる場合のみ受け付け、無効な形式は警告。  
   - 写真アップロード時に拡張子を小文字へそろえ、保存失敗時はロールバック。
2. **検索 UX / テストの整備**  
   - タグフィルタ・お気に入りトグル・フィルタリセットの手動テストをテンプレ化。  
   - 既存データが 50 件を超える場合のページングやパフォーマンスを測り、必要なら `LIMIT / OFFSET` の UI を検討。
3. **手動テストと手順のドキュメント化**  
   - README 手順どおりに `streamlit run → 新規登録 → DB/画像確認` を実施し、確認した結果を README のチェックリストとして追記。  
   - 想定どおりに保存されなかった場合は再現手順と修正策を `docs/known_issues.md`（新規）にまとめる。
4. **レポジトリ運用の整備**  
   - `git status` がクリーンな状態を保てるよう `.env` や `data/` 配下の除外設定を再確認。  
   - コミットメッセージガイドライン（例：`feat: 一覧ビュー追加`）を README 末尾へ追記しておく。

### v0.2（検索・タグ付け）
- [x] タグ・お気に入りフラグ・キーワード検索 UI を追加（`tags` と `favorite` カラムを利用）。
- [x] 一覧ビューでタグピルを表示し、クリックでフィルタリング。
- [x] マイグレーション `002_add_search_indexes.sql` を追加し、よく使う検索列にインデックスを付与。
- [ ] 既存データのクレンジング（タグ重複や空白の整理）→ 必要に応じてスクリプト化。

### v0.3（AI 要約・材料構造化）
- レシピ URL からのスクレイピング → AI 要約パイプラインを `storage.py` / 新規 `ai_pipeline.py` に分離。
- `ai_summary`, `ai_tips`, `ingredients_json` を埋めるバックグラウンド処理を実装し、失敗時はリトライキューへ積む。
- OpenAI / Gemini API キーを `.env` で管理し、投入前にダミー実装でローカル動作確認。

### 保守・開発体験
- requirements のロックファイル導入（`pip-tools` など）と pytest / ruff を CI へ追加。
- Dev Container 内でのポートフォワードや拡張機能トラブルは `conversation_log.md` に記録し、再発時に参照できるようにする。
- 将来的な Firestore / Cloud Storage への移行を見据え、`storage.py` と DB 層をインターフェース化しておく。
