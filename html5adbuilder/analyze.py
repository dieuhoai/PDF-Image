"""Đọc bố cục từ ảnh tham chiếu — chạy offline, không gọi mạng, không dùng AI.

Cách làm: tìm những pixel khác màu nền (gọi là "mực"), gom thành các dải chữ theo hàng ngang,
rồi gom dải thành khối (tiêu đề / mô tả / nút bấm). Mỗi khối cho biết nó nằm ở đâu, rộng bao nhiêu,
chữ to cỡ nào và màu gì — đủ để tool đặt chữ giống ảnh mẫu mà không phải kéo tay từng cái.

Không đọc được chữ trong ảnh, nên tool chỉ chép *chỗ đặt và cỡ chữ*, còn nội dung vẫn là của bạn.
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, UnidentifiedImageError

# Chữ cao bao nhiêu thì cỡ font khoảng bấy nhiêu nhân hệ số này (phần thân chữ không chiếm hết ô chữ).
FONT_FROM_BAND = 1.25
INK_THRESHOLD = 46          # lệch màu nền bao nhiêu thì tính là mực
MIN_BAND_ROWS = 2
CENTER_TOLERANCE = 0.06     # lệch trái/phải dưới ngần này coi như căn giữa
MAX_W = 320                 # thu nhỏ ảnh về bề ngang này cho nhanh


def _rgb_hex(c: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*c)


def _dist(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def _background(px: list[tuple[int, int, int]], w: int, h: int) -> tuple[int, int, int]:
    """Màu nền = màu hay gặp nhất ở viền ảnh."""
    edge: dict[tuple[int, int, int], int] = {}
    for x in range(w):
        for y in (0, h - 1):
            c = px[y * w + x]
            edge[c] = edge.get(c, 0) + 1
    for y in range(h):
        for x in (0, w - 1):
            c = px[y * w + x]
            edge[c] = edge.get(c, 0) + 1
    return max(edge.items(), key=lambda kv: kv[1])[0]


def _bands(ink: list[list[int]], w: int, h: int) -> list[dict]:
    """Các dải chữ theo hàng ngang: hàng nào có mực thì gom lại thành dải."""
    min_ink = max(1, int(w * 0.004))
    rows = [len(cols) for cols in ink]
    bands: list[dict] = []
    start = None
    for y in range(h):
        if rows[y] >= min_ink:
            if start is None:
                start = y
        elif start is not None:
            if y - start >= MIN_BAND_ROWS:
                bands.append({"top": start, "bottom": y})
            start = None
    if start is not None and h - start >= MIN_BAND_ROWS:
        bands.append({"top": start, "bottom": h})

    for b in bands:
        cols = [c for y in range(b["top"], b["bottom"]) for c in ink[y]]
        b["left"], b["right"] = min(cols), max(cols) + 1
        b["h"] = b["bottom"] - b["top"]
    return bands


def _merge_lines(bands: list[dict]) -> list[list[dict]]:
    """Gom các dòng sát nhau, cao gần bằng nhau thành một khối (một đoạn văn)."""
    blocks: list[list[dict]] = []
    for b in bands:
        if blocks:
            prev = blocks[-1][-1]
            gap = b["top"] - prev["bottom"]
            # Hai dòng của cùng một đoạn thì cao gần bằng nhau. Tiêu đề và mô tả cao khác hẳn
            # nên phải tách ra, nếu không tool tưởng là một khối và đặt sai chỗ.
            tall, short = max(b["h"], prev["h"]), min(b["h"], prev["h"])
            similar = short / tall >= 0.72
            if similar and gap <= 0.75 * tall:
                blocks[-1].append(b)
                continue
        blocks.append([b])
    return blocks


def _block_color(px: list[tuple[int, int, int]], ink: list[list[int]], w: int,
                 lines: list[dict], bg: tuple[int, int, int]) -> tuple[int, int, int]:
    """Màu chữ của khối.

    Chỉ lấy 30 % pixel khác nền nhất — viền chữ bị trộn với nền nên nếu lấy trung bình hết
    thì màu ra nhạt hơn màu thật.
    """
    found: list[tuple[float, tuple[int, int, int]]] = []
    for ln in lines:
        for y in range(ln["top"], ln["bottom"]):
            for x in ink[y]:
                c = px[y * w + x]
                found.append((_dist(c, bg), c))
    if not found:
        return (26, 26, 26)
    found.sort(key=lambda t: -t[0])
    core = [c for _, c in found[:max(1, len(found) // 3)]]
    return tuple(round(sum(c[i] for c in core) / len(core)) for i in range(3))  # type: ignore[return-value]


def _align(left: float, right: float) -> str:
    """Căn trái / giữa / phải, suy từ lề hai bên."""
    gap_right = 1.0 - right
    if abs(left - gap_right) <= CENTER_TOLERANCE:
        return "center"
    return "left" if left < gap_right else "right"


def analyze_image(img: Image.Image) -> dict:
    """Trả về bố cục đọc được: nền, các khối chữ kèm vị trí, bề rộng, cỡ chữ, màu."""
    small = img.convert("RGB").copy()
    if small.width > MAX_W:
        small.thumbnail((MAX_W, MAX_W * 4))
    w, h = small.size
    raw = small.tobytes()
    px = [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, len(raw) - 2, 3)]
    bg = _background(px, w, h)

    ink = [[x for x in range(w) if _dist(px[y * w + x], bg) > INK_THRESHOLD] for y in range(h)]
    groups = _merge_lines(_bands(ink, w, h))

    blocks = []
    for lines in groups:
        top = min(ln["top"] for ln in lines)
        bottom = max(ln["bottom"] for ln in lines)
        left = min(ln["left"] for ln in lines)
        right = max(ln["right"] for ln in lines)
        line_h = sorted(ln["h"] for ln in lines)[len(lines) // 2]
        color = _block_color(px, ink, w, lines, bg)
        blocks.append({
            "x": round(left / w, 4), "y": round(top / h, 4),
            "w": round((right - left) / w, 4), "h": round((bottom - top) / h, 4),
            "lines": len(lines),
            "font_ratio": round(line_h * FONT_FROM_BAND / h, 4),
            "align": _align(left / w, right / w),
            "color": _rgb_hex(color),
        })

    return {"bg": _rgb_hex(bg), "size": {"w": img.width, "h": img.height},
            "blocks": blocks, "roles": _roles(blocks, bg)}


def _roles(blocks: list[dict], bg: tuple[int, int, int]) -> dict[str, dict]:
    """Đoán khối nào là tiêu đề / mô tả / nút bấm.

    Quy tắc: khối chữ to nhất ở nửa trên là tiêu đề; khối ngay dưới nó là mô tả;
    khối cuối cùng — nếu tách xa hoặc khác màu hẳn — là nút bấm.
    """
    if not blocks:
        return {}
    ordered = sorted(blocks, key=lambda b: b["y"])
    roles: dict[str, dict] = {}

    head = max(ordered, key=lambda b: b["font_ratio"])
    roles["headline"] = head
    rest = [b for b in ordered if b is not head]
    if not rest:
        return roles

    last = rest[-1]
    text_color = head["color"]
    far = last["y"] - (head["y"] + head["h"]) > 0.18
    different = _dist(_hex_rgb(last["color"]), _hex_rgb(text_color)) > 90
    if (far or different) and last is not head:
        roles["cta"] = last
        rest = rest[:-1]

    below = [b for b in rest if b["y"] > head["y"]]
    if below:
        roles["description"] = below[0]
    return roles


def _hex_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def analyze(path: Path) -> dict:
    try:
        with Image.open(path) as img:
            return analyze_image(img)
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError(f"Không đọc được ảnh {Path(path).name} — hãy dùng file PNG hoặc JPG ({e})") from e


def analyze_bytes(data: bytes) -> dict:
    try:
        with Image.open(io.BytesIO(data)) as img:
            return analyze_image(img)
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError(f"Không đọc được ảnh — hãy dùng file PNG hoặc JPG ({e})") from e
