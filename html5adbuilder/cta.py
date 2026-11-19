"""Kiểm CTA có chứa từ cấm. Danh sách từ cấm lưu ở máy người dùng, sửa được trong tool."""
from __future__ import annotations

from . import catalog as C
from . import defaults as D
from .io_utils import read_json, write_json


def _file():
    return D.USER_DIR / "banned_cta.json"


def _norm(words: list[str]) -> list[str]:
    return sorted({w.strip().lower() for w in words if w and w.strip()})


def load_banned() -> list[str]:
    data = read_json(_file())
    if isinstance(data, list):
        return _norm([str(w) for w in data])
    return _norm(C.DEFAULT_BANNED_CTA)


def save_banned(words: list[str]) -> list[str]:
    clean = _norm(words)
    write_json(_file(), clean)
    return clean


def reset_banned() -> list[str]:
    _file().unlink(missing_ok=True)
    return load_banned()


def find_banned(text: str, words: list[str]) -> list[str]:
    """Trả về các từ cấm có trong text (không phân biệt hoa thường)."""
    low = (text or "").lower()
    return [w for w in words if w in low]
