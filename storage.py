"""写真などのメディア保存ルールを管理するユーティリティ。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent
MEDIA_ROOT = BASE_DIR / "data"
DISH_PHOTO_ROOT = MEDIA_ROOT / "dishes"


def ensure_storage_dirs() -> None:
    """必要なディレクトリを作成する。"""
    DISH_PHOTO_ROOT.mkdir(parents=True, exist_ok=True)


def _sanitize_suffix(filename: Optional[str]) -> str:
    """拡張子を小文字で返す。未指定や不正なら `.jpg` にフォールバック。"""
    if not filename:
        return ".jpg"
    suffix = Path(filename).suffix.lower()
    if not suffix or not re.match(r"^\.[a-z0-9]+$", suffix):
        return ".jpg"
    return suffix


def build_dish_photo_path(dish_id: int, original_filename: Optional[str] = None) -> Path:
    """料理 ID ごとに `data/dishes/<id>/cover.<ext>` を返す。"""
    ensure_storage_dirs()
    dish_dir = DISH_PHOTO_ROOT / str(dish_id)
    dish_dir.mkdir(parents=True, exist_ok=True)
    suffix = _sanitize_suffix(original_filename)
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
