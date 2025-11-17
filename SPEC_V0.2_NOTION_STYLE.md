# CoCock v0.2 — リリース計画（Notion 風フォーマット）

更新日: 2025-11-11
作成者: チーム

---

## 概要
v0.2 の目的は、現行のプロトタイプ（Streamlit + SQLite + ローカルストレージ）を「公開に耐えうる最小限の信頼性と UX」に引き上げることです。短期間（1 週間想定）で実現できる改良に絞り、スパム抑止と匿名投稿の編集体験を改善します。

## 成功基準 (Success Metrics)
- フォーム投稿に対する自動ボット投稿が目に見えて減少すること（定性的）
- 匿名投稿者が自分の投稿を編集するために使うトークンを紛失しにくくなること（定性的）
- CI の smoke test が安定して成功すること（定量: CI パイプラインで 1 回以上通る）

---

## ゴール（短期）
1. reCAPTCHA をオプションで導入してボット投稿を抑止する
2. 匿名投稿の「編集トークン」UX を改善（コピー・ダウンロードのワンクリック）
3. CI に簡易 smoke test を追加して起動確認を自動化する

---

## ユーザーストーリー
- US1: ボット/スクリプトによる大量投稿を減らしたい（運用担当者）
  - 受け入れ基準: reCAPTCHA 有効時に未検証だと投稿できない
- US2: 匿名で投稿したが、あとから編集したい（匿名ユーザー）
  - 受け入れ基準: 投稿後に編集トークンをクリップボードへコピーまたはファイルでダウンロードできる
- US3: 継続的デプロイで、サービスが起動していることを自動で確認したい（開発/CI）
  - 受け入れ基準: CI の smoke step が / に GET して 200 を確認する

---

## スコープ（何を含むか / 何を含めないか）
- 含む
  - Streamlit 側に reCAPTCHA（オプション）を組み込み、環境変数で有効化/無効化を切替可能にする
  - 投稿フローで編集トークンを表示し、「コピー」「ダウンロード」ボタンを追加
  - シンプルな CI smoke test の追加（GitHub Actions の workflow）
- 含めない
  - 認証（OAuth）や DB の本格移行（Cloud SQL）は v0.3 以降とする
  - 画像をクラウドストレージに移す作業は含めない

---

## 受け入れ基準（Acceptance Criteria）
1. reCAPTCHA
   - 環境変数 `RECAPTCHA_SITE_KEY` と `RECAPTCHA_SECRET_KEY` が設定されている場合、投稿フォームに reCAPTCHA UI が表示される
   - reCAPTCHA 検証が通らない投稿はサーバー側で拒否され、ユーザにエラーが表示される
2. 編集トークン UX
   - 匿名投稿完了ページで編集トークンが明示される
   - 「コピー」ボタンでクリップボードにトークンがコピーされる
   - 「ダウンロード」ボタンで `cocock-edit-token-<dish_id>.txt` のようなファイルがダウンロードされる
3. CI smoke
   - GitHub Actions のワークフローでサーバーを起動（ローカルエミュレーション）し、`GET /` が 200 を返すチェックが成功する

---

## 技術仕様（実装の詳細）

### reCAPTCHA（オプション実装）
- フロント: `streamlit_app.py` の投稿フォームに reCAPTCHA ウィジェットを埋める（JS を使うため Streamlit の components を利用）
- バックエンド: フォーム送信時に reCAPTCHA のトークンを受け取り、サーバーサイドで Google の検証 API に問い合わせる
- 設定: `.env` / Cloud Run の環境変数で `RECAPTCHA_SITE_KEY` / `RECAPTCHA_SECRET_KEY` を管理。未設定時は無効化。

注意: Streamlit 単体だと直接 JS を埋めるのがやや面倒（Streamlit Components が必要）。簡易版として「honeypot + reCAPTCHA の server-side チェックのみ（JS はページに script を挿入）」という妥協も選択肢。

### 編集トークン UX
- 現状: `dishes.edit_token` に UUID を保存し、投稿後に表示
- 追加:
  - クライアント側に「コピー」用の JavaScript (Streamlit の components か st.button + pyperclip) を追加
  - 「ダウンロード」ボタンはレスポンスでプレーンテキストを返す小さな streamlit エンドポイントを用意し、`st.markdown` のリンクをクリックでダウンロード

### CI smoke test
- GitHub Actions Workflow `ci/smoke.yml` を追加
  - step: Checkout → Setup Python → Install requirements → Start Streamlit (background) → wait-for 8501 → curl http://localhost:8501/ → assert 200 → stop server

---

## DB / マイグレーション影響
- 既存のマイグレーションは維持。reCAPTCHA とトークン UX は DB スキーマ変更を不要に設計（現状の `edit_token` カラムを利用）

---

## タスク分解と見積り（エンジニア 1 名想定）

1. reCAPTCHA 実装 — 1.5 日
   - サーバー側検証ロジックの追加（0.5 日）
   - フロント側の widget 組み込み（Streamlit Components）と UI（1 日）
   - テスト & ドキュメント（0.5 日）

2. 編集トークン UX — 0.5 日
   - コピー機能の追加（ストリームリットの components or pyperclip fallback）
   - ダウンロードボタンの実装（エンドポイントまたは data: URL）

3. CI smoke test — 0.5 日
   - GitHub Actions ワークフロー作成（0.5 日）

4. ドキュメント更新 & リリースノート — 0.5 日

合計（ラフ）: 3 日

---

## デプロイ手順（v0.2）
1. ブランチ: `release/v0.2` を作成
2. PR を作成し、CI（smoke）が通過することを確認
3. Cloud Run にデプロイ（既存の Cloud Build 設定を利用）
4. 短時間のシャドウモード（モニタリング: ログ・エラー率を 24 時間観察）
5. 問題なければ DNS / 公開手順に従い公開

ロールバック: デプロイ前の安定コミットに Cloud Run をリデプロイ

---

## リスクと軽減策
- reCAPTCHA の導入はユーザー体験を悪化させる可能性がある — オプション化し、段階的に有効化する
- Streamlit + Components での JS 連携は壊れやすい — 代替としてサーバー側検証+簡易 UI で暫定運用
- CI 起動テストはコンテナ差分やネットワークの差で失敗しやすい — 再試行とタイムアウトを長めに設定

---

## リリースチェックリスト（PR マージ前）
- [ ] unit/シンプル確認スクリプトで insert_dish が通る
- [ ] reCAPTCHA 環境変数の有無で UI が切り替わることを確認
- [ ] 編集トークンのコピー/ダウンロードが動作することを手動確認
- [ ] CI smoke test が通ること
- [ ] `README.md` に v0.2 の変更点と環境変数説明を追加

---

## 次のアクション（推奨）
1. これをベースに Issue／PR を作る（私が PR 用のパッチを作成できます）
2. reCAPTCHA の PoC 実装を優先して進める（私に任せる場合: まず server-side 検証を実装します）

---

もしこの Notion 風のページで加えたいセクション（画面モック、具体的な Playwright テストケース、PR のテンプレなど）があれば教えてください。該当ファイルをすぐに作成します。
