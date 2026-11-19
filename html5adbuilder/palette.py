"""Gợi ý bảng màu từ ảnh tham chiếu — chạy offline, không gọi mạng.

Cách làm: thu nhỏ ảnh, lấy màu trung bình có trọng số (bỏ bớt pixel gần trắng/đen tuyệt đối nếu ảnh
còn màu khác), rồi tìm bảng màu có màu nền gần nhất trong không gian màu có tính đến mắt người.
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from . import catalog as C


def _dominant(img: Image.Image) -> tuple[int, int, int]:
    small = img.convert("RGB").copy()
    small.thumbnail((80, 80))
    raw = small.tobytes()
    pixels = [tuple(raw[i:i + 3]) for i in range(0, len(raw) - 2, 3)]
    colored = [p for p in pixels if max(p) - min(p) > 18]  # pixel có màu rõ
    chosen = colored if len(colored) >= max(8, len(pixels) * 0.12) else pixels
    n = max(1, len(chosen))
    return tuple(round(sum(p[i] for p in chosen) / n) for i in range(3))  # type: ignore[return-value]


# Tông màu đại diện của từng bảng màu (độ, 0–360). Ảnh tham chiếu thường đậm hơn nền banner
# rất nhiều, nên so theo *tông màu* mới đúng ý người dùng, không so theo độ sáng.
_HUES = {"blue_trust": 215.0, "green_fresh": 130.0, "warm_cream": 30.0}


def _hsv(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    r, g, b = (c / 255 for c in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d == 0:
        h = 0.0
    elif mx == r:
        h = (60 * ((g - b) / d)) % 360
    elif mx == g:
        h = 60 * ((b - r) / d) + 120
    else:
        h = 60 * ((r - g) / d) + 240
    return h, (0.0 if mx == 0 else d / mx), mx


def _accent(img: Image.Image) -> str | None:
    """Màu nhấn của ảnh: nhóm màu rực nhất, dùng làm màu chữ CTA.

    Gom pixel theo tông màu (12 nhóm) rồi lấy nhóm đông nhất, nên logo hay nút trong ảnh
    tham chiếu sẽ quyết định màu, không bị nền nhạt kéo lệch.
    """
    small = img.convert("RGB").copy()
    small.thumbnail((80, 80))
    raw = small.tobytes()
    buckets: dict[int, list[tuple[int, int, int]]] = {}
    for i in range(0, len(raw) - 2, 3):
        px = (raw[i], raw[i + 1], raw[i + 2])
        h, sat, val = _hsv(px)
        if sat < 0.35 or val < 0.2 or val > 0.97:
            continue
        buckets.setdefault(int(h // 30), []).append(px)
    if not buckets:
        return None
    group = max(buckets.values(), key=len)
    if len(group) < 8:
        return None
    avg = tuple(round(sum(p[i] for p in group) / len(group)) for i in range(3))
    # Màu quá nhạt thì tối đi cho chữ còn đọc được trên nền sáng.
    while _hsv(avg)[2] > 0.82:
        avg = tuple(max(0, round(c * 0.85)) for c in avg)  # type: ignore[assignment]
    return "#{:02x}{:02x}{:02x}".format(*avg)


def _suggest_from_image(img: Image.Image) -> dict:
    dom = _dominant(img)
    hue, sat, val = _hsv(dom)

    if val < 0.35:                       # ảnh tối → nền tối
        ranked = ["dark", "soft_gray", "clean_white"]
        conf = 0.9
    elif sat < 0.12:                     # gần như không màu → trắng/xám
        ranked = (["clean_white", "soft_gray"] if val > 0.9 else ["soft_gray", "clean_white"]) + ["warm_cream"]
        conf = 0.75
    else:
        by_hue = sorted(_HUES, key=lambda k: min(abs(hue - _HUES[k]), 360 - abs(hue - _HUES[k])))
        gap = min(abs(hue - _HUES[by_hue[0]]), 360 - abs(hue - _HUES[by_hue[0]]))
        ranked = [*by_hue, "clean_white"]
        conf = round(max(0.3, 1 - gap / 90), 2)

    best = C.SCHEMES[ranked[0]]
    accent = _accent(img)
    return {
        "scheme": ranked[0],
        "accent": accent,
        "scheme_name": best["name"],
        "dominant": "#{:02x}{:02x}{:02x}".format(*dom),
        "confidence": conf,
        "alternatives": ranked[1:3],
    }


def suggest(path: Path) -> dict:
    try:
        with Image.open(path) as img:
            return _suggest_from_image(img)
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError(f"Không đọc được ảnh {Path(path).name} — hãy dùng file PNG hoặc JPG ({e})") from e


def suggest_bytes(data: bytes) -> dict:
    try:
        with Image.open(io.BytesIO(data)) as img:
            return _suggest_from_image(img)
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError(f"Không đọc được ảnh — hãy dùng file PNG hoặc JPG ({e})") from e
