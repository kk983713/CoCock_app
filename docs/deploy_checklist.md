# デプロイチェックリスト

このファイルは、Cloud Run / GitHub Actions を使ってこのリポジトリを公開・デプロイするための最短チェックリストです。
以下を順に実行すると、main ブランチへの push で自動デプロイされます。

---

## 前提

- `Dockerfile` がリポジトリ直下にあること（本リポジトリに含まれています）。
- `requirements.txt` がルートに存在すること。
- GitHub リポジトリが作成済みであること。

> セキュリティ: サービスアカウントの JSON キーや API キーは絶対にコードに直接コミットしないでください。必ず GitHub Secrets に登録して利用します。

---

## 1) リポジトリを GitHub に公開（public）にする

1. リポジトリの設定(Settings) > General > Repository visibility で Public に変更します。
2. 変更後、`main` ブランチを push しておきます。

（注）Streamlit Community Cloud に公開する場合は public リポジトリが望ましいです。

---

## 2) GitHub Secrets に登録する値

このワークフローで利用するシークレット名（`.github/workflows/deploy-cloud-run.yml` を参照）：

- `GCP_PROJECT_ID` — GCP プロジェクト ID（例: my-gcp-project）
- `GCP_SA_KEY_BASE64` — GCP サービスアカウントの JSON キーを base64 エンコードした文字列

作成例（ローカルで）：

```bash
# JSON キーをダウンロードしてから
base64 < service-account.json | tr -d '\n' > sa_key_base64.txt
# ファイルの中身を GitHub の Secret にコピー
cat sa_key_base64.txt
```

注意: `tr -d '\n'` を使って改行を除去しておくと Secrets 登録が楽になります。

---

## 3) ワークフローの実行/確認方法

1. `main` ブランチに push すると `.github/workflows/deploy-cloud-run.yml` がトリガーされます。
2. Actions タブでワークフロー実行状況を確認できます。失敗時はログを参照して原因（認証 / ビルド / デプロイ）を確認してください。
3. 成功するとワークフローの出力に `CLOUD_RUN_URL` が表示されます（または Cloud Run のサービス詳細から URL を取得可能）。

---

## 4) Streamlit Community Cloud に公開する手順（短縮）

1. GitHub にコードを push（public 推奨）
2. https://share.streamlit.io/ にサインイン（GitHub 認可）
3. New app → リポジトリを選択 → ブランチ `main` → `streamlit_app.py` を選んで Deploy
4. Secrets（環境変数）が必要な場合は Streamlit Cloud の Settings > Secrets に設定

注意点:
- 実行環境はエフェメラル（再起動でローカルファイルは消える）ので画像や DB の永続化は外部ストレージを推奨します。

---

## 5) トラブルシュート（よくある失敗パターン）

- 認証エラー: `GCP_SA_KEY_BASE64` が間違っている、あるいはサービスアカウントに必要権限が無い（`roles/run.admin`, `roles/cloudbuild.builds.builder`, `roles/storage.admin` 等）
- Cloud Build ビルドエラー: `requirements.txt` に不要な/コンパイルが必要なネイティブ依存があると失敗します。ビルドログの `pip` 出力を確認してください。
- ポート関連: Cloud Run ではコンテナ内のアプリは環境変数 `PORT` を参照して起動するようにしてください（Dockerfile の CMD で `streamlit run ... --server.port $PORT` を使う）。

---

## 6) 追加の改善（任意）

- ワークフローを `google-github-actions/setup-gcloud` に置き換えると安定・簡潔に書けます。希望があれば変換します。
- デプロイ前に `gcloud builds submit --no-cache` を試してビルドの再現性をチェックすると良いです。

---

必要なら、私がこのリポジトリに対して README の補足やワークフローの改善パッチを作って PR を出すこともできます。どうしますか？
