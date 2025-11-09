from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Iterable

import streamlit as st

from db import DB_PATH, apply_migrations
from storage import build_dish_photo_path, ensure_storage_dirs


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
) -> int:
    tags_text = tags_to_text(parse_tags_input(tags_raw))
    photo_path: Path | None = None

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dishes (name, memo_user, recipe_url, tags, favorite, is_public)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, memo_user, recipe_url, tags_text, 1 if favorite else 0, 1 if is_public else 0),
        )
        dish_id = cur.lastrowid

        if photo_file is not None:
            sanitized_filename = Path(photo_file.name).name.lower()
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

    if "last_saved_id" not in st.session_state:
        st.session_state["last_saved_id"] = None
    if "tag_filter" not in st.session_state:
        st.session_state["tag_filter"] = []

    st.title("🍳 レシピログ v0.2")
    st.caption("写真・メモ・タグを 1 分で記録して、すぐに検索できる実験用アプリ")

    tabs = st.tabs(["登録フォーム", "一覧 / 検索", "公開ギャラリー"])

    with tabs[0]:
        with st.form("dish_entry_form"):
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

            preview_name = name.strip()
            preview_memo = memo_user.strip()
            can_submit = bool(preview_name or preview_memo)
            if not can_submit:
                st.info("料理名かメモのどちらかは必須です。")
            if recipe_url.strip() and not is_valid_recipe_url(recipe_url.strip()):
                st.warning("参考レシピ URL は http:// または https:// から始めてください。")

            submitted = st.form_submit_button("登録する", disabled=not can_submit)
            if submitted:
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
                    with st.spinner("保存しています…"):
                        dish_id = insert_dish(
                                cleaned_name,
                                cleaned_url,
                                cleaned_memo,
                                tags_raw,
                                favorite_flag,
                                photo_file,
                                is_public=is_public_flag,
                            )
                    st.session_state["last_saved_id"] = dish_id
                    st.success("料理を登録しました。")

        if st.session_state["last_saved_id"]:
            st.info(
                f"最新の登録 ID: {st.session_state['last_saved_id']} — 一覧タブで検索できます。"
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
