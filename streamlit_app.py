from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

import streamlit as st

from db import DB_PATH, apply_migrations
from storage import build_dish_photo_path, ensure_storage_dirs
import uuid
from datetime import datetime
import os
import requests
from passlib.hash import pbkdf2_sha256 as pwd_hasher


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_tags_input(raw: str) -> list[str]:
    """カンマ / 改行 / 全角読点で区切られたタグ文字列を配列へ整形。"""
    if not raw:
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for chunk in re.split(r"[,\s、]+", raw):
        tag = chunk.strip()
        if not tag:
            continue
        lowered = tag.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        tags.append(tag)
    return tags


def tags_to_text(tags: Iterable[str]) -> str:
    return ",".join(tag.strip() for tag in tags if tag.strip())


def split_tags_field(tags_field: str | None) -> list[str]:
    if not tags_field:
        return []
    return [t.strip() for t in tags_field.split(",") if t.strip()]


def is_valid_recipe_url(url: str) -> bool:
    lower = url.lower()
    return lower.startswith("http://") or lower.startswith("https://")


def insert_dish(
    name: str,
    recipe_url: str | None,
    memo_user: str,
    tags_raw: str,
    favorite: bool,
    photo_file,
    is_public: bool = False,
    owner_id: int | None = None,
) -> int:
    tags_text = tags_to_text(parse_tags_input(tags_raw))
    photo_path: Path | None = None

    conn = get_connection()
    try:
        cur = conn.cursor()
        # 柔軟に owner_id に対応する: テーブルに owner_id カラムが存在する場合のみ挿入する
        def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
            cur = conn.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cur.fetchall()]
            return column in cols

        columns = ["name", "memo_user", "recipe_url", "tags", "favorite", "is_public"]
        params: list[object] = [name, memo_user, recipe_url, tags_text, 1 if favorite else 0, 1 if is_public else 0]
        if owner_id is not None and _has_column(conn, "dishes", "owner_id"):
            columns.append("owner_id")
            params.append(owner_id)

        placeholders = ", ".join(["?"] * len(columns))
        sql = f"INSERT INTO dishes ({', '.join(columns)}) VALUES ({placeholders})"
        cur.execute(sql, params)
        dish_id = cur.lastrowid

        if photo_file is not None:
            sanitized_filename = Path(photo_file.name).name.lower()
            # user_id が指定されていれば保存先をユーザースコープにする
            try:
                photo_path = build_dish_photo_path(dish_id, sanitized_filename, user_id=owner_id)
            except TypeError:
                # 互換性: 古い storage.build_dish_photo_path シグネチャの場合は従来の呼び出しにフォールバック
                photo_path = build_dish_photo_path(dish_id, sanitized_filename)
            with photo_path.open("wb") as f:
                f.write(photo_file.getbuffer())
            cur.execute(
                "UPDATE dishes SET photo_path = ? WHERE id = ?",
                (str(photo_path), dish_id),
            )

        # ensure is_public persisted for photo uploads as well
        if is_public:
            cur.execute("UPDATE dishes SET is_public = ? WHERE id = ?", (1, dish_id))

        conn.commit()
        return dish_id
    except Exception:
        conn.rollback()
        if photo_path and photo_path.exists():
            photo_path.unlink(missing_ok=True)
        raise
    finally:
        conn.close()


def fetch_all_tags() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT tags FROM dishes WHERE tags <> ''").fetchall()
    finally:
        conn.close()

    tag_set: set[str] = set()
    for row in rows:
        tag_set.update(split_tags_field(row["tags"]))
    return sorted(tag_set, key=str.lower)


def fetch_dishes(
    keyword: str = "",
    tags: list[str] | None = None,
    favorite_only: bool = False,
    public_only: bool = False,
    limit: int = 50,
) -> list[sqlite3.Row]:
    tags = tags or []
    conn = get_connection()
    try:
        where = ["1=1"]
        params: list[str | int] = []

        if keyword:
            like = f"%{keyword.lower()}%"
            where.append(
                "(LOWER(name) LIKE ? OR LOWER(memo_user) LIKE ? OR LOWER(recipe_url) LIKE ?)"
            )
            params.extend([like, like, like])

        for tag in tags:
            where.append("LOWER(tags) LIKE ?")
            params.append(f"%{tag.lower()}%")

        if favorite_only:
            where.append("favorite = 1")

        if public_only:
            where.append("is_public = 1")

        sql = f"""
            SELECT *
            FROM dishes
            WHERE {' AND '.join(where)}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(limit)
        cur = conn.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


def update_favorite_flag(dish_id: int, favorite: bool) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE dishes SET favorite = ? WHERE id = ?",
            (1 if favorite else 0, dish_id),
        )
        conn.commit()
    finally:
        conn.close()


def render_tag_buttons(tags: list[str], dish_id: int) -> None:
    if not tags:
        return

    cols = st.columns(min(4, len(tags)))
    for idx, tag in enumerate(tags):
        col = cols[idx % len(cols)]
        if col.button(f"#{tag}", key=f"tagpill-{dish_id}-{idx}"):
            current = st.session_state.get("tag_filter", [])
            if tag not in current:
                st.session_state["tag_filter"] = current + [tag]
            st.experimental_rerun()


def render_dish_card(row: sqlite3.Row) -> None:
    tags = split_tags_field(row["tags"])
    favorite = bool(row["favorite"])
    photo_path = Path(row["photo_path"]) if row["photo_path"] else None
    has_photo = photo_path and photo_path.exists()

    container = st.container()
    if has_photo:
        photo_col, body_col = container.columns([1, 2])
        with photo_col:
            st.image(str(photo_path), use_column_width=True)
    else:
        body_col = container

    with body_col:
        title = row["name"] or "名称未設定"
        title_suffix = " ⭐" if favorite else ""
        st.subheader(f"{title}{title_suffix}")
        st.caption(row["created_at"])
        if row["memo_user"]:
            st.write(row["memo_user"])
        if row["recipe_url"]:
            st.markdown(f"[参考レシピを開く]({row['recipe_url']})", help="ブラウザで開く")

        render_tag_buttons(tags, row["id"])

        fav_label = "★ お気に入りを解除" if favorite else "☆ お気に入りにする"
        if st.button(fav_label, key=f"favorite-toggle-{row['id']}"):
            update_favorite_flag(row["id"], not favorite)
            st.experimental_rerun()


def main() -> None:
    st.set_page_config(page_title="Recipe Log", page_icon="🍳", layout="wide")
    apply_migrations()
    ensure_storage_dirs()

    # Temporary debug: write a startup line so we can confirm the active Streamlit
    # process is executing the current code and can write to the workspace path.
    try:
        debug_log = Path("/workspaces/CoCock_app") / "turnstile_debug.log"
        with debug_log.open("a", encoding="utf-8") as df:
            df.write(f"{datetime.utcnow().isoformat()} STARTUP pid={os.getpid()}\n")
    except Exception:
        pass

    if "last_saved_id" not in st.session_state:
        st.session_state["last_saved_id"] = None
    if "tag_filter" not in st.session_state:
        st.session_state["tag_filter"] = []
    if "submissions_in_session" not in st.session_state:
        # ブラウザごとの簡易制限（セッション単位）
        st.session_state["submissions_in_session"] = 0

    # Turnstile token をクエリパラメータから受け取れるようにしておく（turnstile_test.html から自動遷移）
    try:
        # st.experimental_get_query_params は非推奨のため st.query_params を使用する
        params = st.query_params
        candidate = None
        if "turnstile_token" in params and params["turnstile_token"]:
            # query_params の値はリストで返されるため最初の要素を使う
            candidate = params["turnstile_token"][0]
        # If a short id was provided, try to fetch the full token from a local token store
        elif "turnstile_token_id" in params and params["turnstile_token_id"]:
            short_id = params["turnstile_token_id"][0]
            try:
                # Debug: note that server is about to attempt retrieval from token_store
                try:
                    debug_log = Path("/workspaces/CoCock_app") / "turnstile_debug.log"
                    with debug_log.open("a", encoding="utf-8") as df:
                        df.write(f"{datetime.utcnow().isoformat()} ATTEMPT_RETRIEVE id={short_id}\n")
                except Exception:
                    pass
                # token_store をローカルで動かしている場合にのみ試みる (開発用)
                resp = requests.get(f"http://127.0.0.1:8765/retrieve?id={short_id}", timeout=1)
                if resp.status_code == 200:
                    j = resp.json()
                    tok = j.get("token")
                    if tok:
                        candidate = tok
                        print("DEBUG: retrieved turnstile token from local token_store")
                        try:
                            with debug_log.open("a", encoding="utf-8") as df:
                                df.write(f"{datetime.utcnow().isoformat()} SERVER_RETRIEVED id={short_id} len={len(tok)}\n")
                        except Exception:
                            pass
            except Exception:
                # 無理に失敗を伝えず、後続のスキャン処理にフォールバックする
                pass
        else:
            # turnstile_token というキーがなければ、受け取った全てのクエリ値をスキャンして
            # Turnstile のトークンっぽい値 (先頭が 0. で長い) を探す
            for k, v in params.items():
                if not v:
                    continue
                # v はリスト
                for item in v:
                    if isinstance(item, str) and (item.startswith("0.") and len(item) > 20):
                        candidate = item
                        break
                if candidate:
                    break
        if candidate:
            # デバッグ出力（ログに出るのでトラブルシュート時に使える）
            print(f"DEBUG: resolved turnstile token candidate from query params (key may vary)")
            # 追加デバッグ: ファイルにも追記して外部から確認しやすくする
            try:
                # Streamlit may execute the script from a temp path; write debug log to workspace path
                debug_log = Path("/workspaces/CoCock_app") / "turnstile_debug.log"
                with debug_log.open("a", encoding="utf-8") as df:
                    df.write(f"{datetime.utcnow().isoformat()} DEBUG resolved_candidate len={len(candidate)} source=query\n")
            except Exception:
                # ログ失敗は無視して続行
                pass
            # 直接フォーム入力欄を書き換えて即時レンダリング競合を起こすと
            # Streamlit フロントエンドで removeChild の NotFoundError が発生することがあるため
            # 安全のため「候補」として保存し、ユーザーが明示的に適用するか確認するUIを出す。
            st.session_state["turnstile_token_candidate"] = candidate
    except Exception:
        # 古い Streamlit や想定外のエラーが発生しても壊さない
        pass

    st.title("🍳 レシピログ v0.2")
    st.caption("写真・メモ・タグを 1 分で記録して、すぐに検索できる実験用アプリ")

    # デバッグ用表示: クエリパラメータとセッション内の turnstile_token を見やすく出す
    with st.expander("Debug: Turnstile (クエリとセッション)"):
        try:
            st.write("query_params:", st.query_params)
        except Exception:
            st.write("query_params: <unavailable>")
        st.write("session turnstile_token:", st.session_state.get("turnstile_token"))

    # サイドバー：匿名投稿の紐付け（Claim）と簡易プロフィール閲覧
    st.sidebar.header("匿名投稿の紐付け / プロフィール")
    with st.sidebar.expander("匿名投稿をアカウントに紐付ける（Claim）"):
        claim_dish_id = st.text_input("投稿ID", key="claim_dish_id")
        claim_token = st.text_input("編集トークン", key="claim_token")
        claim_username = st.text_input("紐付けるユーザー名", key="claim_username")
        if st.button("紐付けを実行", key="claim_button"):
            if not (claim_dish_id and claim_token and claim_username):
                st.error("投稿ID・編集トークン・ユーザー名を入力してください。")
            else:
                try:
                    cid = int(claim_dish_id)
                except ValueError:
                    st.error("投稿ID は整数で入力してください。")
                else:
                    conn = get_connection()
                    try:
                        cur = conn.cursor()
                        cur.execute("SELECT id FROM dishes WHERE id = ? AND edit_token = ?", (cid, claim_token))
                        row = cur.fetchone()
                        if not row:
                            st.error("投稿が見つからないか、編集トークンが一致しません。")
                        else:
                            # ensure user exists
                            cur.execute("SELECT id FROM users WHERE username = ?", (claim_username,))
                            u = cur.fetchone()
                            if u:
                                user_id = u[0]
                            else:
                                cur.execute("INSERT INTO users (username) VALUES (?)", (claim_username,))
                                user_id = cur.lastrowid
                            cur.execute("UPDATE dishes SET owner_id = ?, edit_token = NULL, edit_token_created_at = NULL WHERE id = ?", (user_id, cid))
                            conn.commit()
                            st.success("投稿をアカウントに紐付けました。プロフィールで確認できます。")
                    finally:
                        conn.close()

    with st.sidebar.expander("プロフィールを見る（ユーザー名で検索）"):
        prof_name = st.text_input("ユーザー名を入力", key="profile_username")
        if st.button("プロフィール表示", key="profile_button"):
            if not prof_name:
                st.error("ユーザー名を入力してください。")
            else:
                conn = get_connection()
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT id FROM users WHERE username = ?", (prof_name,))
                    row = cur.fetchone()
                    if not row:
                        st.info("該当ユーザーが見つかりません。")
                    else:
                        uid = row[0]
                        cur.execute("SELECT COUNT(*) FROM dishes WHERE owner_id = ?", (uid,))
                        cnt = cur.fetchone()[0]
                        st.write(f"投稿数: {cnt}")
                        if cnt >= 10:
                            st.success("Badge: Contributor（投稿10件以上）")
                        # list recipes
                        cur.execute("SELECT id, name, created_at FROM dishes WHERE owner_id = ? ORDER BY created_at DESC LIMIT 100", (uid,))
                        rows = cur.fetchall()
                        for r in rows:
                            st.markdown(f"- [{r[1]}] (ID: {r[0]}) — {r[2]}")
                finally:
                    conn.close()

    # Turnstile セッション検証（PoC）: ログイン / Claim 時に検証してセッションにフラグを立てる
    # 将来的に FastAPI に切り出すことを想定して、ここでは同期的に siteverify へ問い合わせる。
    with st.sidebar.expander("Turnstile セッション検証（PoC）"):
        st.write("アプリ全体で Turnstile を 1 度だけ検証してセッションを信頼するための PoC です。")
        verify_token = st.text_input("Turnstile token を貼って検証する（開発用）", key="verify_token_input")
        verify_ttl_hours = st.number_input("検証の有効期間（時間）", min_value=1, max_value=168, value=1, step=1)
        if st.button("検証してセッションを信頼する", key="do_turnstile_verify"):
            # 本番では TURNSTILE_SECRET がセットされている前提でサーバ側検証を行う
            turnstile_secret = os.environ.get("TURNSTILE_SECRET")
            if not verify_token:
                st.error("token を入力してください（PoC）。")
            else:
                if turnstile_secret:
                    try:
                        resp = requests.post(
                            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                            data={"secret": turnstile_secret, "response": verify_token},
                            timeout=5,
                        )
                        j = resp.json()
                        if j.get("success"):
                            st.session_state["turnstile_verified_at"] = datetime.utcnow().isoformat()
                            st.success("Turnstile 検証に成功しました。セッションを信頼します。")
                        else:
                            st.error("Turnstile の検証に失敗しました: " + str(j))
                    except Exception as e:
                        st.error(f"検証中にエラーが発生しました: {e}")
                else:
                    # 開発時: secret 未設定ならトークンを受け入れてセッションを立てる（安全性に注意）
                    st.warning("TURNSTILE_SECRET が設定されていません — 開発モードで検証をスキップします。")
                    st.session_state["turnstile_verified_at"] = datetime.utcnow().isoformat()
                    st.success("開発モード: セッションを信頼しました。")

        # 現在の検証状態表示
        def _is_turnstile_verified(max_age_seconds: int = 3600) -> bool:
            t = st.session_state.get("turnstile_verified_at")
            if not t:
                return False
            try:
                dt = datetime.fromisoformat(t)
            except Exception:
                return False
            return (datetime.utcnow() - dt).total_seconds() < max_age_seconds

        verified = _is_turnstile_verified(int(verify_ttl_hours * 3600))
        if verified:
            st.success(f"セッション検証済み（有効期限: {verify_ttl_hours} 時間） — 検証時刻: {st.session_state.get('turnstile_verified_at')}")
        else:
            st.info("このブラウザでまだ Turnstile 検証されていません。")

    # Authentication: simple username+password registration & login (PoC)
    with st.sidebar.expander("アカウント（登録 / ログイン）"):
        # Registration
        st.write("新規登録")
        reg_user = st.text_input("新規ユーザー名", key="reg_user")
        reg_pass = st.text_input("新規パスワード", type="password", key="reg_pass")
        if st.button("登録する", key="do_register"):
            if not reg_user or not reg_pass:
                st.error("ユーザー名とパスワードを入力してください。")
            else:
                conn = get_connection()
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT id FROM users WHERE username = ?", (reg_user,))
                    if cur.fetchone():
                        st.error("そのユーザー名は既に使われています。別の名前を選んでください。")
                    else:
                        # Use PBKDF2-SHA256 for development PoC hashing to avoid
                        # environment-specific bcrypt backend issues (bcrypt may
                        # enforce a 72-byte input limit during backend detection
                        # which can raise at import/runtime). PBKDF2-SHA256 is
                        # suitable for PoC and does not have that limitation.
                        ph = pwd_hasher.hash(reg_pass)
                        cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (reg_user, ph))
                        conn.commit()
                        st.success("登録しました。ログインしてください。")
                finally:
                    conn.close()

        st.write("---")
        # Login
        st.write("ログイン")
        login_user = st.text_input("ユーザー名", key="login_user")
        login_pass = st.text_input("パスワード", type="password", key="login_pass")
        if st.button("ログイン", key="do_login"):
            if not login_user or not login_pass:
                st.error("ユーザー名とパスワードを入力してください。")
            else:
                conn = get_connection()
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT id, password_hash FROM users WHERE username = ?", (login_user,))
                    row = cur.fetchone()
                    if not row:
                        st.error("ユーザーが存在しません。")
                    else:
                        uid = row[0]
                        ph = row[1]
                        if not ph:
                            st.error("このアカウントはパスワードが設定されていません。")
                        elif pwd_hasher.verify(login_pass, ph):
                            st.session_state["user_id"] = uid
                            st.session_state["username"] = login_user
                            st.success("ログインしました。投稿フォームに戻って投稿できます。")
                        else:
                            st.error("パスワードが違います。")
                finally:
                    conn.close()

        if st.session_state.get("user_id"):
            if st.button("ログアウト", key="do_logout"):
                st.session_state.pop("user_id", None)
                st.session_state.pop("username", None)
                st.success("ログアウトしました。")

    tabs = st.tabs(["登録フォーム", "一覧 / 検索", "公開ギャラリー"])

    with tabs[0]:
        with st.form("dish_entry_form"):
            # 投稿はログイン必須（匿名投稿を廃止）
            user_id = st.session_state.get("user_id")
            username = st.session_state.get("username") or ""
            if not user_id:
                st.info("投稿するにはログインが必要です。サイドバーの登録/ログインからアカウントでログインしてください。")
            photo_file = st.file_uploader(
                "料理の写真", type=["png", "jpg", "jpeg"], accept_multiple_files=False
            )
            name = st.text_input("料理名", placeholder="鶏むね肉の照り焼き")
            recipe_url = st.text_input("参考レシピ URL", placeholder="https://example.com")
            tags_raw = st.text_input(
                "タグ（カンマ区切り）",
                placeholder="和食,10分,鶏肉",
                help="和食,10分,鶏肉 のようにカンマで区切る。スペースや改行でも分割されます。",
            )
            favorite_flag = st.toggle("また作りたい（お気に入り）に登録する", value=False)
            is_public_flag = st.checkbox("公開する（ギャラリーに表示）", value=False)
            memo_user = st.text_area(
                "メモ",
                placeholder="作った理由や工夫などを書いておけます。",
                height=160,
            )
            # honeypot（スパムボット対策）: 人間は空欄にする想定のフィールド
            honeypot_website = st.text_input(
                "この欄は空のままにしてください（スパム対策）",
                value="",
                help="この欄に値が入っている場合はスパムの可能性が高いです。",
                key="honeypot_website",
            )

            # show session verification hint for logged-in user
            verified_at = st.session_state.get("turnstile_verified_at")
            if user_id:
                if verified_at:
                    st.caption(f"このブラウザは Turnstile 検証済み（検証時刻: {verified_at}）。投稿時の検証は不要です。")
                else:
                    st.caption("このブラウザは Turnstile 未検証です。サイドバーの Turnstile セッション検証を実行してください。")
            turnstile_secret = os.environ.get("TURNSTILE_SECRET")
            if turnstile_secret:
                st.caption("Turnstile が有効化されています。トークンを取得して貼り付けてください（PoC）。")

            preview_name = name.strip()
            preview_memo = memo_user.strip()
            # ヘルプ表示はするが、ボタンは常に有効にしておき、submit 時に必須チェックを行う
            if not (preview_name or preview_memo):
                st.info("料理名かメモのどちらかは必須です。")
            if recipe_url.strip() and not is_valid_recipe_url(recipe_url.strip()):
                st.warning("参考レシピ URL は http:// または https:// から始めてください。")

            # 常にボタンを有効にしておき、押されたらサーバ側で検証する
            submitted = st.form_submit_button("登録する")
            if submitted:
                # サーバ側の必須チェック: 料理名かメモのどちらかが無ければエラーにする
                cleaned_name = name.strip()
                cleaned_memo = memo_user.strip()
                if not (cleaned_name or cleaned_memo):
                    st.error("料理名かメモのどちらかは必須です。")
                    submitted = False
            if submitted:
                # enforce logged-in user requirement
                if not user_id:
                    st.error("投稿するにはログインが必要です。サイドバーでログインしてください。")
                    submitted = False
                else:
                    # If TURNSTILE_SECRET is present, require session verification
                    if turnstile_secret:
                        def _is_turnstile_verified_local(max_age_seconds: int = 3600) -> bool:
                            t = st.session_state.get("turnstile_verified_at")
                            if not t:
                                return False
                            try:
                                dt = datetime.fromisoformat(t)
                            except Exception:
                                return False
                            return (datetime.utcnow() - dt).total_seconds() < max_age_seconds

                        if not _is_turnstile_verified_local(int(verify_ttl_hours * 3600)):
                            st.error("このブラウザは Turnstile 未検証です。サイドバーで検証してから再度送信してください。")
                            submitted = False
                    else:
                        st.warning("TURNSTILE_SECRET 未設定のため、開発モードで検証をスキップします。")
                # If token provided (legacy) verify with Cloudflare
                if submitted and turnstile_secret and st.session_state.get("turnstile_token"):
                    turnstile_token = st.session_state.get("turnstile_token")
                    try:
                        resp = requests.post(
                            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                            data={"secret": turnstile_secret, "response": turnstile_token},
                            timeout=5,
                        )
                        j = resp.json()
                        if not j.get("success"):
                            st.error("Turnstile の検証に失敗しました。投稿はブロックされました。")
                            submitted = False
                    except Exception as e:
                        st.error(f"Turnstile の検証中にエラーが発生しました: {e}")
                        submitted = False
                # honeypot チェック
                if honeypot_website and honeypot_website.strip():
                    # ログに残す（マイグレーションがない場合は無視される）
                    try:
                        conn_log = get_connection()
                        try:
                            conn_log.execute(
                                "INSERT INTO submission_attempts (author_display_name) VALUES (?)",
                                (f"HONEYPOT:{honeypot_website}",),
                            )
                            conn_log.commit()
                        finally:
                            conn_log.close()
                    except Exception:
                        # ログ保存に失敗しても処理は続けずブロックのみ行う
                        pass
                    st.error("不正な入力が検出されました（スパム対策）。投稿は受け付けられません。")
                    submitted = False
                    # フォーム内の処理を中断
                # セッションごとの簡易レート制限
                if submitted and st.session_state.get("submissions_in_session", 0) >= 5:
                    st.error("このブラウザからの投稿が多すぎます。後でもう一度お試しください。")
                    submitted = False
                cleaned_name = name.strip()
                cleaned_url = recipe_url.strip() or None
                cleaned_memo = memo_user.strip()
                errors: list[str] = []
                if cleaned_url and not is_valid_recipe_url(cleaned_url):
                    errors.append("参考レシピ URL は http:// または https:// から始めてください。")

                if errors:
                    for msg in errors:
                        st.error(msg)
                else:
                    if not submitted:
                        # 既に honeypot やセッション制限等でブロックされています。
                        pass
                    else:
                        with st.spinner("保存しています…"):
                            # owner is the logged-in user
                            owner_id: int | None = st.session_state.get("user_id")

                            # DB ベースの頻度チェック（ユーザー単位）: 過去24時間に多すぎる投稿があればブロック
                            try:
                                if owner_id is not None:
                                    conn_chk = get_connection()
                                    try:
                                        cur_chk = conn_chk.cursor()
                                        cur_chk.execute(
                                            "SELECT COUNT(*) FROM dishes WHERE owner_id = ? AND created_at >= datetime('now', '-24 hours')",
                                            (owner_id,),
                                        )
                                        cnt_recent = cur_chk.fetchone()[0]
                                        if cnt_recent >= 20:
                                            st.error("このアカウントからの投稿が多すぎます（24時間以内に20件を超えています）。しばらくお待ちください。")
                                            # ブロックするために submitted を False にする
                                            submitted = False
                                    finally:
                                        conn_chk.close()
                            except Exception:
                                # DB が整っていない（マイグレーション未適用等）の可能性。無視して続行する。
                                pass

                            if submitted:
                                # 実際に保存する
                                dish_id = insert_dish(
                                    cleaned_name,
                                    cleaned_url,
                                    cleaned_memo,
                                    tags_raw,
                                    favorite_flag,
                                    photo_file,
                                    is_public=is_public_flag,
                                    owner_id=owner_id,
                                )

                                # 投稿成功ログを残す（submission_attempts） — マイグレーションがない場合は黙って無視
                                try:
                                    conn_log2 = get_connection()
                                    try:
                                        conn_log2.execute(
                                            "INSERT INTO submission_attempts (author_display_name) VALUES (?)",
                                            (username or None,),
                                        )
                                        conn_log2.commit()
                                    finally:
                                        conn_log2.close()
                                except Exception:
                                    pass

                                # セッション側の状態更新と成功メッセージはここで確実に行う
                                st.session_state["last_saved_id"] = dish_id
                                st.session_state["submissions_in_session"] = st.session_state.get("submissions_in_session", 0) + 1
                                st.success("料理を登録しました。")
                            else:
                                # ここでは submitted == False のケース（頻度チェック等で弾かれた）を扱う
                                if owner_id is None:
                                    st.error("投稿するにはログインが必要です（owner_id が見つかりません）。")
                                # それ以外の理由で submitted=False の場合は既に適切なエラーメッセージが表示されているはず

        if st.session_state["last_saved_id"]:
            st.info(
                f"最新の登録 ID: {st.session_state['last_saved_id']} — 一覧タブで検索できます。"
            )
        # フォーム内では download_button が使えないため、フォームの外でダウンロードボタンを表示する
        if st.session_state.get("pending_edit_download"):
            pd = st.session_state.pop("pending_edit_download")
            st.download_button(
                label="編集リンクをダウンロード",
                data=pd.get("data"),
                file_name=pd.get("file_name"),
                mime="text/plain",
            )

    with tabs[1]:
        all_tags = fetch_all_tags()
        st.subheader("料理一覧")

        search_col, favorite_col = st.columns([3, 1])
        with search_col:
            st.text_input(
                "キーワード検索（料理名 / URL / メモ）",
                key="search_keyword",
                placeholder="鶏 / パスタ / https://example.com",
            )
        with favorite_col:
            favorite_only = st.toggle("お気に入りのみ", key="favorite_only_filter")

        st.multiselect(
            "タグフィルタ",
            options=all_tags,
            key="tag_filter",
            help="タグボタンをクリックしても追加できます。",
        )

        if st.button("フィルタをクリア", type="secondary"):
            st.session_state["search_keyword"] = ""
            st.session_state["favorite_only_filter"] = False
            st.session_state["tag_filter"] = []
            st.experimental_rerun()

        keyword = st.session_state.get("search_keyword", "").strip()
        selected_tags = st.session_state.get("tag_filter", [])
        favorite_only = st.session_state.get("favorite_only_filter", False)

        dishes = fetch_dishes(keyword=keyword, tags=selected_tags, favorite_only=favorite_only)

        st.caption(f"{len(dishes)} 件ヒット（最大 50 件表示）")
        if not dishes:
            st.info("まだ料理が登録されていないか、条件に一致する料理がありません。")
        else:
            for row in dishes:
                render_dish_card(row)

    with tabs[2]:
        st.subheader("公開ギャラリー")
        st.caption("公開フラグが立っているレシピのみ表示します。")

        # simple gallery: show up to 200 public items
        public_items = fetch_dishes(public_only=True, limit=200)
        st.caption(f"{len(public_items)} 件公開中（最大200件表示）")
        if not public_items:
            st.info("公開されているレシピはありません。登録フォームから公開してみましょう。")
        else:
            for row in public_items:
                render_dish_card(row)


if __name__ == "__main__":
    main()
