# CoCock_app 仕様書（Note 記事を参考にしたドラフト）

参考: https://note.com/tanabemg/n/na2db89a5cbda

この仕様書は「早く MVP を回しながら主要な仕様を抑える」ことを目的に、最低限必要な項目をまとめたドラフトです。
必要に応じて Figma／チケットリンク／レビューを付けてブラッシュアップしてください。

## ドキュメント情報
- ドキュメント名: CoCock_app 仕様書（ドラフト）
- バージョン: 0.1
- ステータス: Draft
- 作成者: (自動生成) / 要レビュー: プロダクトオーナー、リードエンジニア
- 関連リンク:
  - リポジトリ: (このワークスペース)
  - マイグレーション一覧: `/migrations`
  - ストレージ案内: `storage.py`

## 目的
CoCock_app は、レシピの写真・メモ・タグを素早く記録し、検索・共有できるログアプリケーションです。MVP の目的は「ユーザーが思い立ったらすぐにレシピを記録でき、あとから検索・編集できる」体験を低摩擦で提供することです。

## KPI（例）
- 1日あたりの新規投稿数（目標：100/月 → まずは 10/日）
- ユーザー継続率（7日、30日）
- 投稿から次の再訪（閲覧 or 再投稿）までの時間
- 検索クリック率（検索→詳細遷移率）

## 対象ユーザー・ロール
- Anonymous visitor: 匿名で投稿・閲覧（編集トークンで後から編集）
- Registered user: ユーザー名で投稿・管理（将来的に OAuth）
- Admin: モデレーション／アプリ設定（将来的）

## 概要（機能一覧）
1. 投稿フォーム
   - 写真アップロード（png/jpg/jpeg）、料理名、参考URL、タグ、メモ、公開フラグ
   - 匿名投稿時に一意の編集トークンを生成して表示（ユーザーが保管）
2. 一覧 / 検索
   - キーワード検索（料理名/メモ/URL）、タグフィルタ、お気に入りフィルタ
3. 公開ギャラリー
   - is_public フラグの付いた投稿を大きめのギャラリー形式で表示
4. プロフィール / ユーザー管理（仮）
   - ユーザー名で紐付け、投稿一覧表示
5. 匿名投稿の Claim（紐付け）
   - 投稿ID と編集トークンを使って投稿をユーザーアカウントに紐付ける
6. スパム防止（MVP 軽量実装）
   - Honeypot、セッション制限、DB ベースの頻度チェック
7. データ永続化
   - SQLite (`receipts.db`) とファイルストレージ（`data/`）

## 画面遷移（高レベル）
- 登録フォーム（/） → 登録成功で「編集トークン（匿名時）」表示 → 一覧タブへ誘導
- 一覧 (/list) → 詳細（/dishes/<id>） → 編集（ログインまたはトークン）
- 公開ギャラリー (/gallery)
- サイドバー：Claim / プロフィール検索

## 画面毎の仕様（主要）
1. 登録フォーム（MVP）
   - 入力項目: ユーザー名（任意）, 写真, 料理名 (必須またはメモ必須), 参考URL (optional), タグ (カンマ区切り), お気に入りフラグ, 公開フラグ, メモ
   - バリデーション: 参考URL は http(s) 始まりのみ許可。料理名 or メモ の両方が空の場合は弾く。
   - ファイル保存: サーバー側で `data/dishes/<dish_id>/cover.<ext>`（将来的に `data/users/<user_id>/dishes/<dish_id>/` もサポート）
   - 成功時: dish_id を返却、匿名なら edit_token を生成して DB に保存しユーザーに一度だけ表示

2. 一覧 / 検索
   - 検索クエリは部分一致（LOWER LIKE %q%）で実装
   - タグフィルタはタグ列文字列の LOWER LIKE %tag% で実装（タグはカンマ区切りで保存）

3. Claim フロー
   - サイドバーで投稿ID と編集トークン、紐付け先ユーザー名を入力
   - サーバーは `SELECT id FROM dishes WHERE id = ? AND edit_token = ?` の検証後、users テーブルに user 作成 or 取得、`owner_id` に設定し `edit_token` を NULL にする

## API（REST） — MVP 用 (内部 API、将来は分離可能)
- POST /api/dishes
  - 説明: 新規投稿（multipart/form-data）
  - 入力: name, recipe_url, memo_user, tags, favorite (0/1), is_public (0/1), photo_file, username (optional)
  - 出力: {id, edit_token?}

- GET /api/dishes
  - 説明: 一覧・検索
  - クエリ: q, tags[], favorite_only, public_only, limit, offset
  - 出力: リスト

- GET /api/dishes/{id}
  - 説明: 詳細取得

- POST /api/dishes/{id}/claim
  - 入力: claim_token, claim_username
  - 処理: token 検証、owner_id 設定、edit_token 削除

## DB スキーマ（現状 / 推奨）
- users
  - id INTEGER PRIMARY KEY
  - username TEXT UNIQUE
  - created_at TIMESTAMP

- dishes
  - id INTEGER PRIMARY KEY
  - name TEXT
  - memo_user TEXT
  - recipe_url TEXT
  - tags TEXT -- カンマ区切り
  - favorite INTEGER (0/1)
  - is_public INTEGER (0/1)
  - photo_path TEXT
  - owner_id INTEGER NULL REFERENCES users(id)
  - author_display_name TEXT NULL
  - edit_token TEXT NULL
  - edit_token_created_at TIMESTAMP NULL
  - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  - updated_at TIMESTAMP

- submission_attempts
  - id INTEGER PRIMARY KEY
  - author_display_name TEXT
  - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

インデックス: dishes(created_at DESC), dishes(owner_id), submission_attempts(author_display_name, created_at)

## ストレージ
- 画像パス: `data/dishes/<dish_id>/cover.<ext>` またはユーザースコープ `data/users/<user_id>/dishes/<dish_id>/cover.<ext>`
- ローカルファイルは本番で GCS/S3 に移行する。署名付き URL を用いフロントから直接アップロードすることでサーバー負荷を削減する。

## セキュリティ / スパム対策
- Honeypot（hidden field）: フォームにボット検知用フィールドを追加。値がある場合は拒否し `submission_attempts` にログ。
- Session 制限: st.session_state によるブラウザセッション単位の投稿回数制限 (例: 5/セッション)
- DB レート制限: owner_id ごとに過去 24 時間の投稿数制限 (例: 20/日)
- 改善候補: reCAPTCHA/hCaptcha、IP ベースのレート制御、メール認証

## ロギング / 監視
- 収集項目: 投稿成功/失敗、Honeypot 検出、Claim 成功/失敗、例外ログ
- メトリクス: 日次投稿数、新規ユーザー数、スパム検出率

## Acceptance Criteria（受け入れ基準）
1. 投稿フォームで有効な入力を送ると DB に dishes レコードが作成される。
2. 匿名投稿時は edit_token が生成され、ユーザーに一度だけ表示される。
3. Claim フローで正しい投稿ID とトークンを入力すると owner_id が設定され edit_token が無効化される。
4. Honeypot に値がある投稿は保存されず submission_attempts にログされる。
5. ユーザーが過度に投稿しようとすると DB レート制限でブロックされる（適切なメッセージを表示）。

## テストケース（簡易）
1. 正常系: 投稿（写真有り/無し）、一覧に反映されるか。
2. 匿名編集: 匿名投稿 → edit_token 表示 → Claim で紐付け。
3. 不正系: honeypot に値を入れて投稿 → 投稿が拒否され、submission_attempts に記録。
4. レート制御: 同一 owner で 21 件連投 → 最後の投稿でブロック。

## 実装スケジュール案（ラフ見積）
- PoC (Fast path; ローカル SQLite + ローカルストレージ): 1週
- MVP (UI 改善、Claim、簡易スパム対策): 2〜3週
- 安定化（テスト, ログ, reCAPTCHA, GCS への画像移行）: +2週

## 将来改善案 / 補足
- 認証: NextAuth / Google OAuth を導入して本格的なユーザー管理へ移行
- ストレージ: GCS/S3 に移行、署名付き URL によるフロント直接アップロード
- DB: SQLite から Postgres (Cloud SQL) に移行
- モデレーション/管理画面の実装

---
このドラフトを元に、優先度の高い機能（Claim、投稿、検索）から実装し、次に運用性（ログ/監視/スパム対策）を整えていくことを推奨します。
