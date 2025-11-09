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

## ローカル接続時の注意: localhost と 127.0.0.1 の違い

開発中にブラウザが「読み込み中（バッファリング）」で止まる場合、`localhost` と `127.0.0.1` の挙動差が原因になることがあります。

- 原因例:
   - `localhost` が IPv6 の `::1` に解決され、サーバが IPv4 のみでリッスンしている。
   - ブラウザ拡張（Proxy/AdBlock 等）やプロキシが `localhost` への接続を妨げている。
   - hosts ファイルが書き換えられている。

推奨される回避策:

1. まず `127.0.0.1` を使ってアクセスしてみてください（例: http://127.0.0.1:8501）。
    - 多くのケースで `127.0.0.1` では問題なく動作します。

2. 常に全インタフェースで待ち受けたい場合（コンテナやリモートからアクセスする場合など）は、起動時に `--server.address 0.0.0.0` を指定してください。

```bash
# ローカル全インタフェースで待ち受け（開発用）
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501

# CORS を無効化して検証する（ローカル開発のみ。公開環境で無効化しないでください）
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.enableCORS false
```

3. ブラウザの拡張を無効化（特に AdBlock / Proxy / セキュリティ系）して再読み込みするか、シークレット/プライベートウィンドウで試してください。

4. hosts の確認（念のため）:

```bash
cat /etc/hosts | sed -n '1,200p'
```

README の補足: 開発環境で `localhost` に問題がある場合は `127.0.0.1` を使うか、上記の `--server.address` オプションを起動スクリプト／Makefile に追記することを推奨します。

## Cloud Run への試験デプロイ
Cloud Run はコンテナをそのまま公開できる Google Cloud サービスです。リポジトリ直下の `Dockerfile` を使えば以下でデモ環境を立ち上げられます。

1. GCP でプロジェクトを作成し、`gcloud` CLI をセットアップ  
   ```bash
   gcloud auth login
   gcloud config set project <PROJECT_ID>
   ```
2. Cloud Build でコンテナを作成  
   ```bash
   gcloud builds submit --tag gcr.io/<PROJECT_ID>/cocock-app:v0.2
   ```
3. Cloud Run へデプロイ（リージョン例: `asia-northeast1`）  
   ```bash
   gcloud run deploy cocock-app \
     --image gcr.io/<PROJECT_ID>/cocock-app:v0.2 \
     --platform managed \
     --region asia-northeast1 \
     --allow-unauthenticated
   ```
4. 発行された URL にアクセスすると Streamlit UI が表示されます。`PORT` は Cloud Run が自動指定し、コンテナ内では `streamlit run ... --server.port ${PORT}` を実行します。

> **注意:** Cloud Run のコンテナファイルシステムはリビジョン更新時やスケール時にリセットされるため、`receipts.db` や `data/` は永続化されません。実際の運用では Cloud SQL / Firestore / Cloud Storage など外部ストレージへ移行する計画が必要です（ロードマップで今後対応）。

### デプロイを自動化するスクリプト
リポジトリに簡単なデプロイスクリプトを追加しました: `scripts/deploy_cloud_run.sh`。

使い方（ローカルに `gcloud` がある前提）:

```bash
# 手動実行例
./scripts/deploy_cloud_run.sh <PROJECT_ID> v0.2

# Makefile を使う場合
make deploy-cloud-run PROJECT_ID=<PROJECT_ID> TAG=v0.2
```

スクリプトは以下を行います:
- `gcloud auth login`（必要に応じて対話）
- `gcloud config set project <PROJECT_ID>`
- `gcloud builds submit --tag gcr.io/<PROJECT_ID>/cocock-app:<TAG>`
- `gcloud run deploy cocock-app --image ... --region asia-northeast1 --allow-unauthenticated`

デプロイが成功するとスクリプトが Cloud Run の URL を `conversation_log.md` に追記します。実行環境側で `gcloud` のセットアップと認証が必要です。

### CI / 非対話型デプロイ
CI 環境でサービスアカウントを使ってデプロイする場合は、`ci/deploy_cloud_run_ci.sh` を使います。対話的認証が不要で、サービスアカウントの JSON キーを利用して gcloud に認証します。

推奨（GitHub Actions 等での使い方）:

1. GCP 側でサービスアカウントを作成し、`roles/run.admin`, `roles/storage.admin`, `roles/cloudbuild.builds.builder` など最低限の権限を付与し、JSON キーを作成してシークレットに登録します。
2. CI のシークレット名例: `GCP_SA_KEY_BASE64` に JSON キーを base64 エンコードして登録。
3. GitHub Actions のステップ例（抜粋）:

```yaml
- name: Deploy to Cloud Run
   env:
      PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
      SERVICE_ACCOUNT_KEY_BASE64: ${{ secrets.GCP_SA_KEY_BASE64 }}
      TAG: v0.2
   run: |
      chmod +x ci/deploy_cloud_run_ci.sh
      ./ci/deploy_cloud_run_ci.sh
```

スクリプトは `CLOUD_RUN_URL=<url>` を出力します。必要であれば CI の出力をパイプして他のジョブに渡してください。

> 注意: CI 用のスクリプトはサービスアカウントキーを扱います。キーの管理（ローテーション・最小権限）は厳密に行ってください。

## v0.2 UI の使い方
1. `streamlit run streamlit_app.py` を実行し、ブラウザでタブが 2 つある画面を開く。
2. **登録フォーム** タブで写真 / 料理名 / URL / メモに加えて「タグ（カンマ区切り）」と「また作りたい（お気に入り）」を入力し、`登録する` を押す。
3. 登録が成功すると「一覧 / 検索」タブに自動反映される。タグが多い場合はボタン（チップ）をクリックすると同じタグでフィルタされる。
4. 一覧タブではキーワード・タグ・お気に入りフラグで即時絞り込みが可能。フィルタをクリアしたい場合は `フィルタをクリア` ボタンを利用する。
5. 各カード右下の「☆ / ★」ボタンでお気に入り状態をトグルでき、その結果は即座に保存される。

## 共有（公開）機能 — 使い方と注意点

このプロジェクトでは「みんなに見せる」ための共有（公開）機能を段階的に実装します。まずは最小実装として匿名で公開できるフラグを追加し、後で認証や外部ストレージへ移行できる設計にします。

簡易公開フロー（MVP）
- ユーザーがレシピ登録フォームで「公開する」チェックを付けると、`dishes` テーブルの `is_public` フラグが立ちます。
- 公開フラグが立っているレコードは「公開ギャラリー」ページでサムネイル付きで一覧表示されます。
- 画像はローカルの `data/dishes/<id>/cover.<ext>` に保存され、UI はそのファイルパスから画像を配信します（ただし永続性に注意）。

Streamlit Community Cloud と永続化について
- Streamlit Community Cloud（無料ホスティング）にデプロイする場合、実行環境のローカルファイルは再デプロイやランタイム再起動で消える可能性があります。つまり、アプリ内でファイルを保存しても永久に保持される保証がありません。
- そのため、公開画像やユーザーアップロードを長期保存する場合は外部ストレージ（Google Cloud Storage / AWS S3 など）を利用してください。外部ストレージを使うことで、複数インスタンス間での共有・高可用性・大容量保管が可能になります。

プライバシーと利用規約（運用時に必要な最低限）
- ユーザーに画像をアップロードさせる際は、著作権・肖像権・個人情報の取り扱いについて利用規約または同意チェックを必ず表示してください。
- 明示的に他人のコンテンツを無断で投稿しないよう注意喚起し、違反時の削除ポリシーを README に記載しておくと安全です。

運用上の推奨設定
- デモ/MVP 終了後は、公開画像は GCS/S3 に移動し、DB は Cloud SQL / Firestore 等のマネージド DB に移行してください。
- まずは「匿名公開（MVP）」で早めに公開し、悪用や規模課題が出てきたら認証（OAuth）やモデレーション機能を追加するワークフローを推奨します。

Streamlit Community Cloud への最短手順（初回のみ手動）
1. リポジトリを GitHub に push する。
2. Streamlit Community にログインし、`New app` → GitHub のリポジトリを選択して初回デプロイを行う（最初の接続はブラウザから手動で行う必要があります）。
3. 以後は `main` ブランチに push すると自動で再ビルド・再デプロイされます。

注: 初回接続のための手動作業は不可避ですが、その後の更新は自動化できます。初期段階では README に手順を載せておくことでユーザーの期待値を管理します。

## 開発ロードマップ
### 現状できていること
- Dev Container・requirements・マイグレーション適用ユーティリティまで整備済み
- `streamlit_app.py` の v0.2 で写真 / 料理名 / URL / メモ / タグ / お気に入りを登録し、同画面の一覧タブで即検索・フィルタできる
- 会話ログや仕様メモ (`recipe_log_mvp_spec.md`) で決定事項を追える状態

### 直近 TODO (v0.2 仕上げ)
1. **検索 UX / テストの整備**  
   - タグフィルタ・お気に入りトグル・フィルタリセットの手動テストをテンプレ化。  
   - 既存データが 50 件を超える場合のページングやパフォーマンスを測り、必要なら `LIMIT / OFFSET` の UI を検討。
2. **手動テストと手順のドキュメント化**  
   - README 手順どおりに `streamlit run → 新規登録 → DB/画像確認` を実施し、確認した結果を README のチェックリストとして追記。  
   - 想定どおりに保存されなかった場合は再現手順と修正策を `docs/known_issues.md`（新規）にまとめる。
3. **レポジトリ運用の整備**  
   - `git status` がクリーンな状態を保てるよう `.env` や `data/` 配下の除外設定を再確認。  
   - コミットメッセージガイドライン（例：`feat: 一覧ビュー追加`）を README 末尾へ追記しておく。

### v0.2（検索・タグ付け）
- [x] タグ・お気に入りフラグ・キーワード検索 UI を追加（`tags` と `favorite` カラムを利用）。
- [x] 一覧ビューでタグピルを表示し、クリックでフィルタリング。
- [x] マイグレーション `002_add_search_indexes.sql` を追加し、よく使う検索列にインデックスを付与。
- [x] 入力フォームに必須チェック（料理名 or メモ）と URL 形式検証、画像保存失敗時のロールバック処理を追加。
- [x] Cloud Run 用の `Dockerfile` / `.dockerignore` を整備し、`gcloud run deploy` で公開できる状態にした。
- [ ] 既存データのクレンジング（タグ重複や空白の整理）→ 必要に応じてスクリプト化。
- [ ] 永続ストレージ（Cloud SQL / Firestore など）へのデータ移行計画を策定。

### v0.3（AI 要約・材料構造化）
- レシピ URL からのスクレイピング → AI 要約パイプラインを `storage.py` / 新規 `ai_pipeline.py` に分離。
- `ai_summary`, `ai_tips`, `ingredients_json` を埋めるバックグラウンド処理を実装し、失敗時はリトライキューへ積む。
- OpenAI / Gemini API キーを `.env` で管理し、投入前にダミー実装でローカル動作確認。

### 保守・開発体験
- requirements のロックファイル導入（`pip-tools` など）と pytest / ruff を CI へ追加。
- Dev Container 内でのポートフォワードや拡張機能トラブルは `conversation_log.md` に記録し、再発時に参照できるようにする。
- 将来的な Firestore / Cloud Storage への移行を見据え、`storage.py` と DB 層をインターフェース化しておく。
