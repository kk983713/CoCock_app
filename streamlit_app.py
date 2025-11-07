import sqlite3

import streamlit as st

from db import DB_PATH, apply_migrations
from storage import build_dish_photo_path, ensure_storage_dirs


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def insert_dish(
    name: str,
    recipe_url: str | None,
    memo_user: str,
    photo_file,
) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dishes (name, memo_user, recipe_url)
            VALUES (?, ?, ?)
            """,
            (name, memo_user, recipe_url),
        )
        dish_id = cur.lastrowid

        if photo_file is not None:
            photo_path = build_dish_photo_path(dish_id, photo_file.name)
            with photo_path.open("wb") as f:
                f.write(photo_file.getbuffer())
            cur.execute(
                "UPDATE dishes SET photo_path = ? WHERE id = ?",
                (str(photo_path), dish_id),
            )

        conn.commit()
        return dish_id
    finally:
        conn.close()


def main() -> None:
    st.set_page_config(page_title="Recipe Log", page_icon="🍳", layout="centered")
    apply_migrations()
    ensure_storage_dirs()

    st.title("🍳 レシピログ v0.1 プロトタイプ")
    st.caption("写真とメモを 1 分で記録する実験用フォーム")

    if "last_saved_id" not in st.session_state:
        st.session_state["last_saved_id"] = None

    with st.form("dish_entry_form"):
        photo_file = st.file_uploader(
            "料理の写真", type=["png", "jpg", "jpeg"], accept_multiple_files=False
        )
        name = st.text_input("料理名", placeholder="鶏むね肉の照り焼き")
        recipe_url = st.text_input("参考レシピ URL", placeholder="https://example.com")
        memo_user = st.text_area(
            "メモ",
            placeholder="作った理由や工夫などを書いておけます。",
            height=160,
        )

        submitted = st.form_submit_button("登録する")
        if submitted:
            cleaned_name = name.strip()
            cleaned_url = recipe_url.strip() or None
            cleaned_memo = memo_user.strip()

            with st.spinner("保存しています…"):
                dish_id = insert_dish(
                    cleaned_name,
                    cleaned_url,
                    cleaned_memo,
                    photo_file,
                )
            st.session_state["last_saved_id"] = dish_id
            st.success("料理を登録しました。")

    if st.session_state["last_saved_id"]:
        st.info(
            f"最新の登録 ID: {st.session_state['last_saved_id']} — 一覧ページは今後追加予定です。"
        )


if __name__ == "__main__":
    main()
