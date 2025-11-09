## Quick: Streamlit Community Cloud にすぐ公開する

短く手早く公開したい場合の最低手順です。

1. リポジトリを GitHub に push（公開リポジトリ推奨）。
2. https://share.streamlit.io/ にログイン（GitHub 認可）。
3. New app → リポジトリを選択 → ブランチに `main` → アプリファイル `streamlit_app.py` を選んで Deploy。
4. 必要なら Settings → Secrets で環境変数（API キー等）を追加。

Notes:
- ローカルファイル（画像や SQLite）はランタイムの再起動で消える可能性があります。永続化が必要なら外部ストレージを使ってください。
