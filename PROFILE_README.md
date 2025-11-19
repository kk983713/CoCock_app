<!--
  GitHub プロフィール README (日本語) - このファイルをコピーして
  github.com/kk983713/kk983713 の README.md に貼り付けてください。
-->

# CoCock

写真付きレシピを素早く記録・検索するプロトタイプです。

- フロントエンド: Streamlit
- トークンプロキシ: FastAPI ベースの短縮IDサーバ（token_store）
- 永続化: SQLite（ローカル開発）

主な特徴:

- 匿名で投稿されたレシピを「短縮ID（short_id）」で安全に扱い、編集トークンをクライアントに直接渡さない設計を採用しています。
- Playwright を使ったヘッドレス E2E による自動検証と、スクリーンショット／HTML スナップショットをアーティファクトとして保存します。

補足資料（PDF）やデモのスクリーンショットをリポジトリに含めています。以下のリンクはコピペして自分のアカウントに合わせてください。

- リポジトリ: https://github.com/<kk983713>/CoCock_app
- 補足PDF: https://github.com/<kk983713>/CoCock_app/raw/main/docs/cocock_supplementary.pdf

---

短縮サマリ（1行）:

CoCock — 写真付きレシピを即記録・検索するプロトタイプ。匿名投稿を後から本人に安全に紐付ける短縮IDプロキシを実装しています。
