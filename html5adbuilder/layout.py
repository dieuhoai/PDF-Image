"""Tính bố cục một creative: cỡ chữ, xuống dòng, vị trí từng thành phần.

Đây là **một nguồn sự thật duy nhất** cho cả bản HTML và bản PNG (ADR 0002), nên hai bản luôn giống nhau.
Toạ độ tính bằng pixel, gốc ở góc trên-trái khung.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from . import catalog as C
from . import fonts
from .models import AdSize, Creative, Design, Pos

MIN_FONT = 8.0
BOLD_ELEMENTS = ("headline", "cta", "badge")   # những khối in đậm, đo bằng font đậm cho khớp
BADGE_PAD_X = 0.45   # đệm ngang của badge, theo cỡ chữ
CTA_PAD_X = 0.75
CTA_PAD_Y = 0.45


class Box(BaseModel):
    element: str
    x: float
    y: float
    w: float
    h: float
    font_size: float = 0
    lines: list[str] = Field(default_factory=list)
    align: str = "center"


class Layout(BaseModel):
    size: AdSize
    boxes: list[Box]
    rtl: bool = False
    warnings: list[str] = Field(default_factory=list)
    mode: str = "center"

    def box(self, element: str) -> Box | None:
        return next((b for b in self.boxes if b.element == element), None)


def _pad(size: AdSize) -> float:
    """Lề trong: nhỏ theo khung, nhưng không bao giờ dưới 3 px."""
    return max(3.0, round(min(size.w, size.h) * 0.07, 1))


def _mode(size: AdSize, requested: str) -> str:
    if requested != "auto":
        return requested
    ratio = size.w / size.h
    # Chỉ banner vừa dẹt vừa thấp mới xếp hàng ngang; khổ to như 970x250 xếp dọc cho chữ lớn, đỡ trống giữa.
    if ratio >= 3.0 and size.h <= 120:
        return "row"
    if ratio <= 0.5:        # cột dọc cao
        return "center"
    return "center"


def _base_font(size: AdSize, mode: str) -> float:
    """Cỡ chữ headline khởi điểm, theo chiều nhỏ của khung."""
    short = min(size.w, size.h)
    if mode == "row":
        return max(MIN_FONT, min(short * 0.34, 30.0))
    return max(MIN_FONT, min(short * 0.13, 34.0))


def pad_for(size: AdSize) -> float:
    """Lề trong của một khung — dùng chung với phần đọc bố cục từ ảnh mẫu."""
    return _pad(size)


def auto_font_sizes(size: AdSize, design: Design) -> dict[str, float]:
    """Cỡ chữ tool tự tính cho từng thành phần (chưa nhân hệ số người dùng chỉnh)."""
    base = _base_font(size, _mode(size, design.layout))
    return {"headline": base, "description": base * 0.56, "cta": base * 0.6, "badge": base * 0.34}


def build(cr: Creative, design: Design, positions: dict[str, Pos] | None = None,
          scales: dict[str, float] | None = None, widths: dict[str, float] | None = None) -> Layout:
    """Tính bố cục.

    `positions`: vị trí người dùng kéo thả (tỉ lệ 0–1), ưu tiên hơn vị trí tự tính.
    `scales`: hệ số cỡ chữ người dùng chỉnh cho từng thành phần (1.0 = cỡ tự tính).
    `widths`: bề rộng ô chữ người dùng kéo (phần của bề rộng dùng được, 1.0 = hết chiều ngang).
    """
    size, content = cr.size, cr.content
    lang = content.lang
    rtl = lang in C.RTL_LANGS
    mode = _mode(size, design.layout)
    pad = _pad(size)
    avail_w = max(1.0, size.w - pad * 2)
    warnings: list[str] = []

    scale = 1.0
    boxes: list[Box] = []
    while True:
        boxes, overflow = _try(cr, design, mode, pad, avail_w, scale, scales or {}, widths or {})
        if not overflow:
            break
        if _base_font(size, mode) * scale <= MIN_FONT:
            warnings.append(f"{size.key}: chữ vẫn tràn ở cỡ nhỏ nhất — hãy rút ngắn nội dung")
            break
        scale *= 0.9

    if positions:
        boxes = [_moved(b, positions.get(b.element), size) for b in boxes]
    boxes = _badge_to_free_corner(boxes, size, pad, fixed=bool(positions and "badge" in positions))
    return Layout(size=size, boxes=boxes, rtl=rtl, warnings=warnings, mode=mode)


def _overlaps(a: Box, b: Box) -> bool:
    return not (a.x + a.w <= b.x + 1 or b.x + b.w <= a.x + 1
                or a.y + a.h <= b.y + 1 or b.y + b.h <= a.y + 1)


def _badge_to_free_corner(boxes: list[Box], size: AdSize, pad: float, fixed: bool) -> list[Box]:
    """Nhãn góc tự né sang góc còn trống khi nó đè lên chữ.

    Chữ có thể đã được kéo lên sát góc trên-trái (hoặc chép theo ảnh mẫu), lúc đó nhãn mặc định
    nằm đúng chỗ đó. Nhãn do tool tự đặt nên dịch nó đi là an toàn; nhãn người dùng tự kéo thì giữ nguyên.
    """
    if fixed:
        return boxes
    badge = next((b for b in boxes if b.element == "badge"), None)
    if badge is None:
        return boxes
    others = [b for b in boxes if b is not badge]
    if not any(_overlaps(badge, o) for o in others):
        return boxes
    corners = [(size.w - pad - badge.w, pad),                    # trên-phải
               (pad, size.h - pad - badge.h),                    # dưới-trái
               (size.w - pad - badge.w, size.h - pad - badge.h)]  # dưới-phải
    for x, y in corners:
        cand = badge.model_copy(update={"x": round(max(0.0, x), 1), "y": round(max(0.0, y), 1)})
        if not any(_overlaps(cand, o) for o in others):
            return [cand if b is badge else b for b in boxes]
    return boxes


def _moved(b: Box, pos: Pos | None, size: AdSize) -> Box:
    if pos is None:
        return b
    x = min(max(0.0, pos.x * size.w), max(0.0, size.w - b.w))
    y = min(max(0.0, pos.y * size.h), max(0.0, size.h - b.h))
    return b.model_copy(update={"x": round(x, 1), "y": round(y, 1)})


def _try(cr: Creative, design: Design, mode: str, pad: float, avail_w: float,
         scale: float, scales: dict[str, float], widths: dict[str, float]) -> tuple[list[Box], bool]:
    """Thử xếp với một hệ số cỡ chữ. Trả về (các hộp, có tràn hay không)."""
    size, content, lang = cr.size, cr.content, cr.content.lang
    # Cỡ gốc của khung; cỡ từng thành phần = cỡ gốc × tỉ lệ mặc định × hệ số người dùng chỉnh.
    base = _base_font(size, mode) * scale
    hl_px = max(MIN_FONT, round(base * scales.get("headline", 1.0), 1))
    desc_px = max(MIN_FONT, round(base * 0.56 * scales.get("description", 1.0), 1))
    cta_px = max(MIN_FONT, round(base * 0.6 * scales.get("cta", 1.0), 1))
    badge_px = max(MIN_FONT, round(base * 0.34 * scales.get("badge", 1.0), 1))
    gap = max(2.0, round(base * 0.3, 1))

    badge: Box | None = None
    if cr.badge:
        label = C.badge_label(cr.badge, lang)
        bw = fonts.text_width(label, badge_px, lang, bold=True) + badge_px * BADGE_PAD_X * 2
        bh = fonts.line_height(badge_px) + badge_px * 0.2
        badge = Box(element="badge", x=pad, y=pad, w=round(bw, 1), h=round(bh, 1),
                    font_size=badge_px, lines=[label], align="center")

    cta_text = content.cta
    # Kiểu "chữ" không có nền nên không cần đệm quanh chữ.
    pad_x, pad_y = (CTA_PAD_X, CTA_PAD_Y) if design.cta_style == "button" else (0.0, 0.0)
    cta_w = fonts.text_width(cta_text, cta_px, lang, bold=True) + cta_px * pad_x * 2
    cta_h = fonts.line_height(cta_px) + cta_px * pad_y * 2

    if mode == "row":
        return _row(cr, badge, pad, avail_w, hl_px, desc_px, gap, cta_text, cta_px, cta_w, cta_h, widths)

    # ---- xếp dọc: badge / headline / description / CTA, căn giữa hoặc trái ----
    align = "left" if mode == "left" else "center"
    hl_limit = avail_w * widths.get("headline", 1.0)
    desc_limit = avail_w * widths.get("description", 1.0)
    hl_lines, hl_w, hl_h = fonts.block_size(content.headline, hl_px, lang, hl_limit, bold=True)
    desc_lines, desc_w, desc_h = fonts.block_size(content.description, desc_px, lang, desc_limit)
    # Người dùng đã kéo hẹp ô thì giữ đúng bề rộng đó, chữ căn trong ô.
    if "headline" in widths:
        hl_w = hl_limit
    if "description" in widths:
        desc_w = desc_limit

    top = pad + (badge.h + gap if badge else 0)
    if mode == "top_bottom":
        blocks_h = hl_h + (gap + desc_h if desc_lines else 0)
        y = top
    else:
        blocks_h = hl_h + (gap + desc_h if desc_lines else 0) + gap + cta_h
        y = max(top, (size.h - blocks_h) / 2 + (badge.h + gap if badge and mode != "center" else 0))
        y = max(top, min(y, size.h - pad - blocks_h)) if blocks_h + top + pad <= size.h else top

    boxes: list[Box] = [badge] if badge else []
    cur = y
    hl_box = Box(element="headline", x=_x(align, pad, avail_w, hl_w), y=round(cur, 1), w=round(hl_w, 1),
                 h=round(hl_h, 1), font_size=hl_px, lines=hl_lines, align=align)
    boxes.append(hl_box)
    cur += hl_h
    if desc_lines:
        cur += gap
        boxes.append(Box(element="description", x=_x(align, pad, avail_w, desc_w), y=round(cur, 1),
                         w=round(desc_w, 1), h=round(desc_h, 1), font_size=desc_px, lines=desc_lines, align=align))
        cur += desc_h

    if mode == "top_bottom":
        cta_y = size.h - pad - cta_h
    else:
        cta_y = cur + gap
    cta_box = Box(element="cta", x=_x(align, pad, avail_w, cta_w), y=round(cta_y, 1), w=round(cta_w, 1),
                  h=round(cta_h, 1), font_size=cta_px, lines=[cta_text], align="center")
    boxes.append(cta_box)

    bottom = max(b.y + b.h for b in boxes)
    too_wide = any(b.w > avail_w + 0.5 for b in boxes)
    overflow = bottom > size.h - pad + 0.5 or too_wide
    return _clamp(boxes, size, pad), overflow


def _row(cr: Creative, badge: Box | None, pad: float, avail_w: float, hl_px: float, desc_px: float,
         gap: float, cta_text: str, cta_px: float, cta_w: float, cta_h: float,
         widths: dict[str, float]) -> tuple[list[Box], bool]:
    """Banner dẹt: chữ bên trái, nút bên phải, badge nằm cạnh chữ."""
    size, content, lang = cr.size, cr.content, cr.content.lang
    left = pad + (badge.w + gap if badge else 0)
    text_w = max(1.0, size.w - pad - cta_w - gap - left)
    hl_lines, hl_w, hl_h = fonts.block_size(content.headline, hl_px, lang,
                                            text_w * widths.get("headline", 1.0), bold=True)
    desc_lines, desc_w, desc_h = fonts.block_size(content.description, desc_px, lang,
                                                  text_w * widths.get("description", 1.0))
    if "headline" in widths:
        hl_w = text_w * widths["headline"]
    if "description" in widths:
        desc_w = text_w * widths["description"]
    # Banner dẹt thường không đủ chỗ cho description → chỉ giữ khi còn thừa chiều cao.
    if desc_lines and hl_h + gap * 0.5 + desc_h > size.h - pad * 2:
        desc_lines, desc_w, desc_h = [], 0.0, 0.0
    block_h = hl_h + (gap * 0.5 + desc_h if desc_lines else 0)
    y = max(pad, (size.h - block_h) / 2)

    boxes: list[Box] = []
    if badge:
        boxes.append(badge.model_copy(update={"y": round(max(pad, (size.h - badge.h) / 2), 1)}))
    boxes.append(Box(element="headline", x=round(left, 1), y=round(y, 1), w=round(hl_w, 1), h=round(hl_h, 1),
                     font_size=hl_px, lines=hl_lines, align="left"))
    if desc_lines:
        boxes.append(Box(element="description", x=round(left, 1), y=round(y + hl_h + gap * 0.5, 1),
                         w=round(desc_w, 1), h=round(desc_h, 1), font_size=desc_px, lines=desc_lines, align="left"))
    boxes.append(Box(element="cta", x=round(size.w - pad - cta_w, 1), y=round(max(pad, (size.h - cta_h) / 2), 1),
                     w=round(cta_w, 1), h=round(cta_h, 1), font_size=cta_px, lines=[cta_text], align="center"))

    overflow = (hl_w > text_w + 0.5 or block_h > size.h - pad * 2 + 0.5 or cta_h > size.h - pad + 0.5
                or text_w <= hl_px)
    return _clamp(boxes, size, pad), overflow


def _x(align: str, pad: float, avail_w: float, w: float) -> float:
    return round(pad if align == "left" else pad + (avail_w - w) / 2, 1)


def _clamp(boxes: list[Box], size: AdSize, pad: float) -> list[Box]:
    """Chốt chặn cuối: không để hộp nào ra ngoài khung (dù nội dung quá dài)."""
    out: list[Box] = []
    for b in boxes:
        w = min(b.w, float(size.w))
        h = min(b.h, float(size.h))
        x = min(max(0.0, b.x), max(0.0, size.w - w))
        y = min(max(0.0, b.y), max(0.0, size.h - h))
        out.append(b.model_copy(update={"x": round(x, 1), "y": round(y, 1), "w": round(w, 1), "h": round(h, 1)}))
    return out
