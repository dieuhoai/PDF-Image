"""Vẽ bản PNG tĩnh từ đúng bố cục đã tính (ADR 0002) — không cần trình duyệt."""
from __future__ import annotations

import io

from PIL import Image, ImageDraw

from . import catalog as C
from . import fonts
from . import layout as L
from .models import Creative, Design, Pos
from .render_html import colors


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _gradient(img: Image.Image, c_from: str, c_to: str) -> None:
    """Gradient chéo 135° — vẽ theo từng dòng cho nhanh, đủ mượt ở cỡ banner."""
    a, b = _rgb(c_from), _rgb(c_to)
    w, h = img.size
    px = img.load()
    denom = max(1, w + h - 2)
    for y in range(h):
        for x in range(w):
            t = (x + y) / denom
            px[x, y] = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[assignment]


def _rounded(draw: ImageDraw.ImageDraw, box: L.Box, radius: float, fill: tuple[int, int, int]) -> None:
    draw.rounded_rectangle([box.x, box.y, box.x + box.w, box.y + box.h], radius=max(0, radius), fill=fill)


def _draw_lines(draw: ImageDraw.ImageDraw, box: L.Box, color: tuple[int, int, int], lang: str,
                center_v: bool = False, bold: bool = False) -> None:
    """Vẽ từng dòng chữ. Dùng mốc giữa dòng (anchor "m") nên chữ không bị lệch lên/xuống."""
    f = fonts.font_for(box.font_size, bold, lang)
    stroke = int(round(fonts.bold_stroke(box.font_size, lang))) if bold else 0
    lh = fonts.line_height(box.font_size)
    total = lh * len(box.lines)
    y = box.y + (box.h - total) / 2 if center_v else box.y
    for line in box.lines:
        w = fonts.text_width(line, box.font_size, lang, bold) / fonts.SAFETY
        if box.align == "left":
            x, anchor = box.x, "lm"
        elif box.align == "right":
            x, anchor = box.x + box.w, "rm"
        else:
            x, anchor = box.x + box.w / 2, "mm"
        try:
            draw.text((x, y + lh / 2), line, font=f, fill=color, anchor=anchor,
                      stroke_width=stroke, stroke_fill=color)
        except (ValueError, AttributeError):      # font bitmap không hỗ trợ anchor
            draw.text((box.x if box.align == "left" else box.x + (box.w - w) / 2,
                       y + (lh - box.font_size) / 2), line, font=f, fill=color)
        y += lh


def _scaled(box: L.Box, k: float) -> L.Box:
    return box.model_copy(update={"x": box.x * k, "y": box.y * k, "w": box.w * k, "h": box.h * k,
                                  "font_size": box.font_size * k})


def render_image(cr: Creative, design: Design, positions: dict[str, Pos] | None = None,
                 scales: dict[str, float] | None = None, widths: dict[str, float] | None = None,
                 px_scale: int = 1) -> Image.Image:
    """Vẽ creative ra ảnh. `px_scale` = 2 hoặc 3 cho ảnh nét, bố cục giữ nguyên y hệt."""
    lay = L.build(cr, design, positions, scales, widths)
    col = colors(cr.scheme, design.gradient, design.cta_color)
    size = cr.size
    lang = cr.content.lang
    k = max(1, int(px_scale))
    cw, ch = size.w * k, size.h * k

    if design.gradient != "none":
        img = Image.new("RGB", (cw, ch), (255, 255, 255))
        g = C.GRADIENTS[design.gradient]
        _gradient(img, g["from"], g["to"])
    else:
        img = Image.new("RGB", (cw, ch), _rgb(col["bg"]))
    draw = ImageDraw.Draw(img)
    if design.gradient == "none":
        draw.rectangle([0, 0, cw - 1, ch - 1], outline=_rgb(col["border"]), width=k)

    for element in ("badge", "headline", "description", "cta"):
        raw = lay.box(element)
        if raw is None:
            continue
        b = _scaled(raw, k)
        if element == "badge":
            bb = C.BADGES[cr.badge or "new"]
            _rounded(draw, b, b.h / 2, _rgb(bb["bg"]))
            _draw_lines(draw, b, _rgb(bb["text"]), lang, center_v=True, bold=True)
        elif element == "cta":
            if design.cta_style == "button":
                _rounded(draw, b, min(6 * k, b.h / 4), _rgb(col["cta_bg"]))
                _draw_lines(draw, b, _rgb(col["cta_text"]), lang, center_v=True, bold=True)
            else:
                _draw_lines(draw, b, _rgb(col["cta_bg"]), lang, center_v=True, bold=True)
        elif element == "headline":
            _draw_lines(draw, b, _rgb(col["text"]), lang, bold=True)
        else:
            _draw_lines(draw, b, _rgb(col["sub"]), lang)
    return img


def png_bytes(cr: Creative, design: Design, positions: dict[str, Pos] | None = None,
              scales: dict[str, float] | None = None,
              widths: dict[str, float] | None = None, px_scale: int = 1) -> bytes:
    buf = io.BytesIO()
    render_image(cr, design, positions, scales, widths, px_scale).save(buf, format="PNG", optimize=True)
    return buf.getvalue()
