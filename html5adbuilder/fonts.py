"""Đo chữ và xuống dòng.

Vì bản HTML do trình duyệt người xem render, số đo ở đây chỉ cần *gần đúng*: dùng để chọn cỡ chữ
và cảnh báo tràn. Đo bằng Pillow với một font Unicode của hệ thống (có gì dùng nấy), cộng thêm biên
an toàn SAFETY để bù sai khác font giữa các máy.
"""
from __future__ import annotations

import functools
from pathlib import Path

from PIL import ImageFont, features

from . import catalog as C

SAFETY = 1.08  # chừa 8 % vì máy người xem có thể dùng font rộng hơn

# Font ưu tiên theo hệ điều hành — chọn loại phủ nhiều bảng chữ.
_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    r"C:\Windows\Fonts\arialuni.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]

# Hệ số bù bề rộng cho bảng chữ mà font đo được không phủ (ô vuông .notdef hẹp hơn chữ thật).
_WIDTH_FACTOR = {"ko": 1.0, "ja": 1.0, "zh": 1.0, "th": 1.0, "hi": 1.0, "ar": 1.0}
_CJK_RATIO = 1.0  # bề rộng một chữ CJK ≈ 1.0 × cỡ chữ


# Bản đậm thật của hệ thống: (đường dẫn, số thứ tự mặt chữ trong file .ttc).
# Mỗi font chỉ có một số bảng chữ — Arial Bold không có chữ Hàn, nên phải thử xem font
# có thật sự vẽ được chữ đó không, nếu không sẽ ra một dãy ô vuông.
_BOLD_CANDIDATES: list[tuple[str, int]] = [
    ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0),   # Latin (có dấu tiếng Việt), Ả Rập
    ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 6),          # Hàn + Nhật + Trung
    ("/System/Library/Fonts/Supplemental/Thonburi.ttc", 1),     # Thái
    ("/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc", 1),   # Hindi
    ("/System/Library/Fonts/GeezaPro.ttc", 1),                  # Ả Rập
    ("/System/Library/Fonts/HelveticaNeue.ttc", 1),
    (r"C:\Windows\Fonts\malgunbd.ttf", 0),                    # Hàn (Windows)
    (r"C:\Windows\Fonts\YuGothB.ttc", 0),                     # Nhật (Windows)
    (r"C:\Windows\Fonts\msyhbd.ttc", 0),                      # Trung (Windows)
    (r"C:\Windows\Fonts\arialbd.ttf", 0),
    (r"C:\Windows\Fonts\segoeuib.ttf", 0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
    ("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", 0),
]

# Chữ đại diện để thử xem font có bảng chữ đó không.
# Tiếng Việt phải thử bằng chữ có dấu: font Hàn có chữ Latin thường nhưng thiếu "ế", "Đ".
_SAMPLE = {"ko": "가", "ja": "あ", "zh": "字", "th": "ก", "ar": "ع", "hi": "अ", "vi": "ế"}
_MISSING = "\ue000"          # ô trống riêng tư — font nào cũng vẽ thành ô vuông .notdef


def _ink(font, ch: str) -> int:
    """Tổng độ đậm khi vẽ một ký tự — dùng để so với ô vuông .notdef."""
    from PIL import Image, ImageDraw
    img = Image.new("L", (48, 48), 0)
    ImageDraw.Draw(img).text((8, 8), ch, font=font, fill=255)
    return sum(img.tobytes())


def _covers(path: str, index: int, ch: str) -> bool:
    try:
        f = ImageFont.truetype(path, 20, index=index)
    except OSError:
        return False
    return _ink(f, ch) != _ink(f, _MISSING)


@functools.lru_cache(maxsize=32)
def _bold_face(lang: str = "en") -> tuple[str, int] | None:
    """Mặt chữ đậm vẽ được ngôn ngữ này; không có thì trả None để quay về tô dày nét."""
    sample = _SAMPLE.get(lang, "A")
    for path, index in _BOLD_CANDIDATES:
        if Path(path).is_file() and _covers(path, index, sample):
            return path, index
    return None


@functools.lru_cache(maxsize=1)
def _regular_path() -> str | None:
    for p in _CANDIDATES:
        if Path(p).is_file():
            return p
    return None


@functools.lru_cache(maxsize=2048)
def _font(px: int, bold: bool = False, lang: str = "en"):
    face = _bold_face(lang) if bold else None
    if face:
        try:
            return ImageFont.truetype(face[0], px, index=face[1])
        except OSError:
            pass
    path = _regular_path()
    if path:
        try:
            return ImageFont.truetype(path, px)
        except OSError:  # font hỏng hoặc không đọc được → dùng font kèm Pillow
            pass
    return ImageFont.load_default(size=px)


def font_for(px: float, bold: bool = False, lang: str = "en"):
    """Font Pillow dùng để vẽ PNG (cũng là font dùng để đo)."""
    return _font(max(1, int(round(px))), bold, lang)


@functools.lru_cache(maxsize=1)
def shapes_complex_text() -> bool:
    """Máy có thư viện xếp chữ phức tạp (raqm) không.

    Thiếu nó thì dấu tiếng Thái, Ả Rập, Hindi bị đặt sai chỗ khi *vẽ ảnh PNG*.
    Bản HTML5 không ảnh hưởng vì trình duyệt tự xếp chữ.
    """
    try:
        return bool(features.check("raqm"))
    except Exception:  # noqa: BLE001 — Pillow cũ không có hàm này
        return False


def has_real_bold(lang: str = "en") -> bool:
    return _bold_face(lang) is not None


def bold_stroke(px: float, lang: str = "en") -> float:
    """Chỉ tô dày viền khi máy không có font đậm thật cho bảng chữ này, và tô rất nhẹ."""
    return 0.0 if has_real_bold(lang) else max(0.5, px * 0.022)


def _is_wide(ch: str) -> bool:
    o = ord(ch)
    return (0x1100 <= o <= 0x11FF or 0x2E80 <= o <= 0xA4CF or 0xAC00 <= o <= 0xD7A3
            or 0xF900 <= o <= 0xFAFF or 0xFF00 <= o <= 0xFF60 or 0xFFE0 <= o <= 0xFFE6)


def text_width(text: str, px: float, lang: str = "en", bold: bool = False) -> float:
    """Bề rộng gần đúng của một dòng, đã cộng biên an toàn."""
    if not text:
        return 0.0
    f = font_for(px, bold, lang)
    try:
        w = float(f.getlength(text))
    except (OSError, ValueError):  # glyph thiếu
        w = 0.0
    # Ký tự CJK thường bị đo thiếu khi font không phủ → tính lại theo ô vuông.
    wide = sum(1 for ch in text if _is_wide(ch))
    if wide:
        narrow_w = float(f.getlength("".join(ch for ch in text if not _is_wide(ch))) or 0)
        w = max(w, narrow_w + wide * px * _CJK_RATIO)
    return w * SAFETY * _WIDTH_FACTOR.get(lang, 1.0)


def line_height(px: float) -> float:
    return px * 1.25


def wrap(text: str, px: float, lang: str, max_w: float, bold: bool = False) -> list[str]:
    """Xuống dòng cho vừa max_w. Ngôn ngữ không dùng khoảng trắng thì cắt theo ký tự."""
    text = (text or "").strip()
    if not text:
        return []
    if lang in C.CHAR_WRAP_LANGS or (" " not in text and text_width(text, px, lang, bold) > max_w):
        return _wrap_chars(text, px, lang, max_w, bold)
    lines: list[str] = []
    cur = ""
    for word in text.split():
        cand = f"{cur} {word}".strip()
        if cur and text_width(cand, px, lang, bold) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    # Từ đơn vẫn quá dài → cắt tiếp theo ký tự.
    out: list[str] = []
    for ln in lines:
        out.extend(_wrap_chars(ln, px, lang, max_w, bold) if text_width(ln, px, lang, bold) > max_w else [ln])
    return out


def _wrap_chars(text: str, px: float, lang: str, max_w: float, bold: bool = False) -> list[str]:
    lines: list[str] = []
    cur = ""
    for ch in text:
        if cur and text_width(cur + ch, px, lang, bold) > max_w:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines or [text]


def block_size(text: str, px: float, lang: str, max_w: float,
               bold: bool = False) -> tuple[list[str], float, float]:
    """(các dòng, bề rộng thật, chiều cao) của một khối chữ."""
    lines = wrap(text, px, lang, max_w, bold)
    if not lines:
        return [], 0.0, 0.0
    w = max(text_width(ln, px, lang, bold) for ln in lines)
    return lines, w, line_height(px) * len(lines)
