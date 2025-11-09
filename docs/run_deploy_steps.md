# Runbook: GitHub → Cloud Run デプロイ手順（詳細）

このドキュメントは、ローカルで作業せずに GitHub Actions を使って Cloud Run にデプロイする際の具体手順です。CI の Secrets 登録やワークフローの確認方法までを記載します。

## 1) リポジトリを GitHub に push

1. リモートリポジトリを作成（GitHub）して `main` に push します。

## 2) Secrets 登録

GitHub のリポジトリ → Settings → Secrets and variables → Actions に以下を登録してください:

- `GCP_PROJECT_ID` - GCP プロジェクト ID
- `GCP_SA_KEY` - サービスアカウントの JSON（そのまま全文を Secret に貼り付ける）

（代替）もし `GCP_SA_KEY_BASE64` を使いたければ `docs/deploy_checklist.md` の手順で base64 化して登録し、ワークフローを調整してください。

### サービスアカウントの作成とダウンロード（GCP コンソール）

1. GCP Console → IAM & Admin → Service Accounts → Create Service Account
2. 必要な権限を付与: `Cloud Run Admin (roles/run.admin)`, `Cloud Build Editor (roles/cloudbuild.builds.builder)`, `Storage Admin (roles/storage.admin)` （必要に応じて最小権限に調整）
3. JSON キーを生成してダウンロード

## 3) トリガーと確認

1. `main` ブランチに push すると Actions タブでワークフローが実行されます。
2. 実行中にログを確認し、Build / Deploy ステップの出力を追います。
3. 成功後、Outputs または Cloud Run のサービス詳細から URL を取得します。

## 4) ローカルでのテスト（任意）

1. ローカルで Docker ビルドと Cloud Build の動作を再現したい場合:

```bash
# ローカルでコンテナをビルド
docker build -t cocock-app:local .

# ローカルで起動して動作確認
docker run -p 8501:8501 cocock-app:local
```

注: Cloud Run では起動時に `PORT` 環境変数が渡されるため、Dockerfile の CMD に `streamlit run streamlit_app.py --server.port $PORT` を指定してください。

## 5) よくある失敗と対処

- 認証エラー: Secret の JSON が壊れているか、サービスアカウントに権限が足りない。
- ビルドエラー: `requirements.txt` にネイティブビルドが必要な依存がある。ビルドログの pip 出力を精査。
- ポートが見つからない: コンテナ内で `streamlit` が `$PORT` を使って起動しているか確認。

## 6) 実際の作業を私がサポートする時の流れ

1. あなたが GitHub にリポジトリを push して public にする（私側でリポジトリ操作はできないため）
2. あなたが Secrets を登録する（または一時的に私が案内するコマンドを実行して登録する）
3. main に push して Actions 実行 → 私がログ参照の方法と、失敗時の修正案を提示します。
