"""写真などのメディア保存ルールを管理するユーティリティ。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent
MEDIA_ROOT = BASE_DIR / "data"
DISH_PHOTO_ROOT = MEDIA_ROOT / "dishes"
USER_MEDIA_ROOT = MEDIA_ROOT / "users"


def ensure_storage_dirs() -> None:
    """必要なディレクトリを作成する。

    既存の動作を壊さないため、data/dishes を必ず作成します。
    ユーザースコープのパスを使う場合は users 配下も作成されます。
    """
    DISH_PHOTO_ROOT.mkdir(parents=True, exist_ok=True)
    USER_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def _sanitize_suffix(filename: Optional[str]) -> str:
    """拡張子を小文字で返す。未指定や不正なら `.jpg` にフォールバック。"""
    if not filename:
        return ".jpg"
    suffix = Path(filename).suffix.lower()
    if not suffix or not re.match(r"^\.[a-z0-9]+$", suffix):
        return ".jpg"
    return suffix


def build_dish_photo_path(
    dish_id: int,
    original_filename: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Path:
    """写真の保存パスを返す。

    既存の呼び出しとの互換性を保つため、`user_id` が指定されない場合は従来の
    `data/dishes/<dish_id>/cover.<ext>` を返します。`user_id` を指定すると
    `data/users/<user_id>/dishes/<dish_id>/cover.<ext>` に保存されます。
    """
    ensure_storage_dirs()
    suffix = _sanitize_suffix(original_filename)

    if user_id is None:
        dish_dir = DISH_PHOTO_ROOT / str(dish_id)
    else:
        dish_dir = USER_MEDIA_ROOT / str(user_id) / "dishes" / str(dish_id)

    dish_dir.mkdir(parents=True, exist_ok=True)
    return dish_dir / f"cover{suffix}"


def public_url_for_photo(photo_path: Path) -> str:
    """公開用の URL / パスを返すヘルパ。

    現在はローカルファイルパスをそのまま返します。将来的に GCS/S3 を使う場合は
    環境変数で切り替えられるようにここを集約してください。
    """
    # NOTE: Streamlit の `st.image()` はローカルパスや URL を受け取れるため
    # ここではシンプルに文字列化して返します。
    try:
        return str(photo_path)
    except Exception:
        return ""
