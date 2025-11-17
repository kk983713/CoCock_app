# CoCock: Turnstile ハイブリッド防御設計（C: ハイブリッド）

この文書は「C: ハイブリッド」戦略（ログイン済ユーザはログイン時の Turnstile 検証で以降の投稿を許可、匿名や未検証は投稿ごとに Turnstile を要求）を CoCock_app に導入するための設計仕様書です。

目的
- スパム投稿を抑制しつつ、ログイン済ユーザには良い UX を提供する。
- 将来的に検証ロジックを FastAPI に切り出し、スケーラブルかつ監査しやすいアーキテクチャを可能にする。

想定読者
- 実装担当者、テスター、運用担当者

## 1. 高レベル要件

- サイトの投稿は「ログインユーザ」か「匿名（ただし投稿ごとに Turnstile 必須）」のみ許可する。
- ログイン時に Turnstile を通過するとサーバ側で `verified_at` を記録し、TTL 内は追加検証を不要にする（例: 1 時間）。
- Turnstile の検証はサーバ側で行う（Cloudflare siteverify）。
- ログは敏感情報（トークン本体）を残さない。

## 2. データモデル変更（DB）

目的: ユーザ管理と検証フラグを保持する

推奨マイグレーション（SQLite）: `migrations/006_add_user_auth_and_verified_at.sql`

```sql
-- 例: 既存 users テーブルに password_hash と verified_at を追加
ALTER TABLE users ADD COLUMN password_hash TEXT;
ALTER TABLE users ADD COLUMN email TEXT;
ALTER TABLE users ADD COLUMN verified_at TEXT; -- ISO datetime UTC
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
```

注意:
- 既存 `users` テーブルが無ければ上記を調整。マイグレーションはバックアップを取ってから適用。
- `verified_at` はユーザ単位の最終 Turnstile 検証時刻（UTC ISO）を保持する。TTL 判定はアプリ側で行う。

## 3. API 設計（FastAPI に切り出す想定）

将来的に検証を FastAPI に切り出す場合のエンドポイント（PoC では Streamlit が直接 siteverify しても良い）：

- POST /verify
  - 入力: {"token": "...", "user_id": 123 (任意)}
  - 処理: Cloudflare siteverify を呼び、成功時に `users.verified_at` を更新（もし user_id 提供あり）。
  - 出力: {"success": true, "verified_at": "2025-11-12T12:34:56Z"}
  - 認証: Streamlit -> FastAPI 間は内部通信のためシンプルな API_KEY で保護（環境変数）。

- POST /peek? (token_store 用) — オプション
  - 開発用の token_store に対応する場合、/peek と /retrieve を分ける設計を推奨。

セキュリティ:
- FastAPI は rate-limit（例えば 10 req/min/IP）を追加。
- API_KEY は環境変数で管理し、Cloud Run へは Secret Manager を使用。

## 4. Streamlit UI 変更点

1. サイドバー: 認証 UI
   - 登録フォーム（username, password）およびログインフォームを実装する。
   - ログイン成功時に `st.session_state['user_id']` と `st.session_state['username']` をセット。

2. サイドバー: Turnstile セッション検証（PoC / FastAPI 経由）
   - ログイン済ユーザはサイドバーの「検証」ボタンで Turnstile を通し、成功時に backend (/verify) を呼んで `users.verified_at` を更新。
   - UI は検証済みか否か（残りTTL）を表示する。

3. 投稿フォームのロジック
   - 投稿前に `st.session_state['user_id']` が無ければ投稿できない（必須登録化） — ※C の場合は匿名も許可する選択肢を残すが今回は「ユーザ登録を推奨、匿名は投稿ごと検証」。
   - 投稿時の振る舞い:
     - ユーザがログインかつ `users.verified_at` が TTL 内なら、投稿はそのまま受け付け。
     - ログインだが未検証 or TTL 切れの場合はサイドバーで検証か投稿時の追加検証を要求する。
     - 匿名（許可する場合）は投稿フォームに Turnstile トークン入力欄を表示して投稿ごとに siteverify を実行する。

4. メッセージ/エラー表示
   - 検証失敗は明確に UI で示し、再試行手順を提示する。

## 5. セキュリティ設計

- 全ての siteverify はサーバ側で secret を使って行う（TURNSTILE_SECRET 環境変数）。
- トークン本体はログに残さない（ログは id / user / 時刻 のみ）。
- パスワードは `passlib[bcrypt]` を使ってハッシュ化し、ソルトは自動で管理。
- セッション周り: st.session_state を短期トークンとして利用。長期セッションを実装する場合は cookie と secure backend を検討。
- Rate-limit: 投稿 API に対して IP レベルとユーザレベルの rate-limit を適用。

## 6. 運用・監視

指標（メトリクス）:
- verification_attempts, verification_success_rate
- blocked_submissions, spam_reports
- rate_limit_triggers

アラート:
- verification_success_rate が急落（例: 連続 5 分で 50% 低下）したら通知。
- blocked_submissions が急増したら運用担当へアラート。

ログ:
- 監査ログに検証の成功/失敗を残す（truncated errors, timestamp, user_id, IP）。

## 7. テスト計画

- 単体テスト
  - siteverify 成功/失敗のハンドリング（Mock を使う）。
  - verified_at TTL の判定ロジック。
- 結合テスト（E2E）
  - 登録→ログイン→Turnstile 検証→投稿（成功）
  - 匿名投稿: POST with token -> success/failure
  - レート制限・異常系のテスト
- 自動化
  - Playwright を使って headless フローを回す（token_store の /peek を使って自動化が token を消費しない設計）。

## 8. 移行計画（既存匿名投稿の扱い）

段階的移行を推奨:
- フェーズ 1: 新規投稿はユーザ登録必須にする（匿名投稿を UI で非推奨に）。既存データはそのまま保持する。
- フェーズ 2: 既存投稿に対して Claim ワークフローを強化し、編集権の移譲を進める（ユーザに Claim を促す通知）。
- フェーズ 3: 完全に匿名投稿を廃止する場合は古い匿名投稿の表示/編集ルールを定義（例: 編集は運営承認のみ）。

## 9. マイグレーション/実装タスク（実行順）

短期タスク（PoC → リリース）:
1. `migrations/006_add_user_auth_and_verified_at.sql` を追加。
2. `requirements.txt` に `passlib[bcrypt]` を追加（pip install）。
3. `streamlit_app.py` に: 登録/ログイン/ログアウト UI を追加、st.session_state に user 情報を保存。投稿フォームをログイン必須化（匿名は投稿ごと検証オプション）。
4. siteverify 呼び出しロジックを共通関数に抽出（将来 FastAPI 化しやすくするため）。
5. 自動化: `scripts/auto_turnstile_peek.py` を作成して E2E を回す。

中期タスク（堅牢化）:
1. FastAPI scaffold `services/turnstile_api` を作成し `/verify` 実装。
2. Streamlit を `/verify` へ切り替え（API_KEY で保護）。
3. Rate-limit, monitoring を追加。

## 10. 開発用の簡易コマンド例

（開発環境での簡易チェック）

```bash
# DB マイグレーション（簡易）
python db.py

# 開発サーバ起動
./scripts/start_token_store.sh  # dev token proxy
./scripts/start_streamlit.sh

# E2E テスト（自動化）
/workspaces/CoCock_app/.venv/bin/python /tmp/auto_turnstile_playwright.py
```

## 11. 監査チェックリスト（リリース前）

- [ ] TURNSTILE_SECRET を環境で設定している
- [ ] パスワードハッシュが `passlib[bcrypt]` で保存される
- [ ] トークン本体がログに残らないことを確認
- [ ] rate-limit の閾値が設定されている
- [ ] E2E テスト（登録/検証/投稿）が通る

## 12. 次のステップ（私が代行可能）

- (A) 上の短期タスクを実装して E2E を実行（30〜90分の作業）。
- (B) まずは DB マイグレーションファイルだけ作成してレビュー。 
- (C) FastAPI scaffold を作成し PoC を試す（中期、作業量大）。

一言で指示してください（例: "A を実行して"）。

---
ドキュメント終わり。必要ならこのファイルを README にリンク追加や、migrations/ファイルの自動生成なども実行します。
