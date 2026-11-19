"""Biến bố cục đọc từ ảnh mẫu (analyze.py) thành vị trí + cỡ chữ cho mọi kích thước.

Vị trí lưu theo tỉ lệ khung nên một ảnh mẫu 1200×630 dùng được cho cả 300×250 lẫn 728×90.
Cỡ chữ thì quy về hệ số so với cỡ tool tự tính, có chặn trên chặn dưới để khổ nhỏ không vỡ.
"""
from __future__ import annotations

from . import fonts
from . import layout as L
from .models import MAX_SCALE, MAX_WIDTH, MIN_SCALE, MIN_WIDTH, AdSize, ContentSet, Design, Pos

ROLE_ELEMENTS = ("headline", "description", "cta")
BOOST_CAP = 2.2            # khổ nhỏ được phóng chữ tối đa ngần này lần so với ảnh mẫu
# Chặn hai đầu so với cỡ chữ tool tự tính: giữ được "ý" của ảnh mẫu mà không ra chữ bé tí
# hay to quá khung. Mô tả thường dài nên chặn chặt hơn tiêu đề.
SCALE_RANGE = {"headline": (0.7, 2.2), "description": (0.8, 1.4), "cta": (0.7, 2.0)}


def _boost(ref_w: int, size_w: int) -> float:
    """Ảnh mẫu rộng 1920 mà banner chỉ 300 thì chép y nguyên tỉ lệ sẽ ra chữ bé tí.

    Khổ càng nhỏ, chữ càng phải chiếm phần lớn hơn thì mới đọc được — đây là hệ số bù.
    """
    if size_w <= 0:
        return 1.0
    return min(BOOST_CAP, max(1.0, (ref_w / size_w) ** 0.45))


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _text_of(content: ContentSet, element: str) -> str:
    return {"headline": content.headline, "description": content.description, "cta": content.cta}[element]


def from_analysis(analysis: dict, sizes: list[AdSize], design: Design,
                  sets: list[ContentSet] | None = None) -> dict:
    """Trả về {positions, scales, widths, cta_color, layout} áp cho từng kích thước.

    Có nội dung thật (`sets`) thì cỡ chữ tính theo **bề ngang chữ chiếm trong ảnh mẫu**:
    ảnh mẫu tiêu đề nằm gọn một dòng chiếm 40 % bề ngang thì bản tạo ra cũng vậy.
    Tính theo chiều cao chữ như trước sẽ ra chữ quá to và bị ngắt dòng ở khung hẹp.
    """
    roles = analysis.get("roles") or {}
    if not roles:
        return {"positions": {}, "scales": {}, "widths": {}, "cta_color": "", "layout": design.layout}

    positions: dict[str, dict[str, Pos]] = {}
    scales: dict[str, dict[str, float]] = {}
    widths: dict[str, dict[str, float]] = {}

    head = roles.get("headline", {})
    align = head.get("align", "center")
    guessed_layout = {"left": "left", "right": "left"}.get(align, "center")

    # Cỡ chữ quy theo *cạnh ngắn* của khung, không theo chiều cao: khung dọc 300x600 mà tính
    # theo chiều cao thì chữ to gấp đôi và đè lên nhau.
    ref = analysis.get("size") or {}
    ref_h = max(1, int(ref.get("h") or 1))
    ref_w = max(1, int(ref.get("w") or 1))
    ref_short = max(1, min(ref_w, ref_h))

    for size in sizes:
        auto = L.auto_font_sizes(size, design.model_copy(update={"layout": guessed_layout}))
        pad = L.pad_for(size)
        avail = max(1.0, size.w - pad * 2)
        pos: dict[str, Pos] = {}
        sc: dict[str, float] = {}
        wd: dict[str, float] = {}

        for element in ROLE_ELEMENTS:
            block = roles.get(element)
            if not block:
                continue
            pos[element] = Pos(x=_clamp(block["x"], 0, 1), y=_clamp(block["y"], 0, 1))
            base = auto.get(element, 0) or 1
            want_px = block["font_ratio"] * ref_h / ref_short * min(size.w, size.h)
            sc[element] = round(_clamp(want_px / base, MIN_SCALE, MAX_SCALE), 2)
            # Chỉ chép bề rộng khi ảnh mẫu cố ý ngắt dòng (từ 2 dòng trở lên).
            # Khối một dòng thì bề rộng chỉ là độ dài câu chữ của ảnh, chép sang sẽ ngắt dòng vô lý.
            if element in ("headline", "description") and block.get("lines", 1) >= 2:
                wd[element] = round(_clamp(block["w"] * size.w / avail, MIN_WIDTH, MAX_WIDTH), 3)

        # Bản "chung cho mọi bộ" chỉ dùng khi chưa có nội dung để đo. Có nội dung rồi thì mỗi bộ
        # một bản riêng — nếu không, khung chật mà bản chung vẫn áp vào sẽ làm chữ đè nhau.
        if not sets:
            positions[size.key] = pos
            scales[size.key] = sc
            widths[size.key] = wd

        # Có nội dung thật thì đo chữ và xếp lại cho khỏi đè nhau, theo từng bộ.
        for content in sets or []:
            placed = _place(size, roles, content, auto, pad, avail, ref_h, ref_short, ref_w)
            if placed is None:
                continue                       # khung quá chật → để tool tự bố cục
            key = f"{content.id}/{size.key}"
            positions[key], scales[key], widths[key] = placed

    cta = roles.get("cta") or {}
    return {
        "positions": positions,
        "scales": scales,
        "widths": widths,
        "cta_color": cta.get("color", ""),
        "layout": guessed_layout,
    }


def _place(size: AdSize, roles: dict, content: ContentSet, auto: dict[str, float], pad: float,
           avail: float, ref_h: int, ref_short: int, ref_w: int = 0) -> tuple[dict, dict, dict] | None:
    """Xếp các khối cho một bộ nội dung ở một kích thước, đo chữ thật nên không bị đè nhau.

    Trả về None khi khung quá chật — lúc đó để tool tự bố cục còn hơn ép theo ảnh mẫu rồi vỡ.
    """
    gap = max(2.0, round(min(size.w, size.h) * 0.06, 1))
    shrink = 1.0
    for _ in range(10):
        items = _measure(size, roles, content, auto, avail, ref_h, ref_short, shrink, ref_w)
        if not items:
            return None
        bottom = _stack(items, size, pad, gap)
        if bottom <= size.h - pad + 0.5:
            pos = {it["element"]: Pos(x=_clamp(it["x"] / size.w, 0, 1), y=_clamp(it["y"] / size.h, 0, 1))
                   for it in items}
            sc = {it["element"]: it["scale"] for it in items}
            wd = {it["element"]: it["width"] for it in items if it.get("width")}
            return pos, sc, wd
        shrink *= 0.88
        if min(it["scale"] for it in items) <= MIN_SCALE:
            return None
    return None


def _measure(size: AdSize, roles: dict, content: ContentSet, auto: dict[str, float], avail: float,
             ref_h: int, ref_short: int, shrink: float, ref_w: int = 0) -> list[dict]:
    """Mỗi khối: cỡ chữ theo ảnh mẫu, rồi đo xem chiếm bao nhiêu chỗ thật."""
    items: list[dict] = []
    for element in ROLE_ELEMENTS:
        block = roles.get(element)
        text = _text_of(content, element) if block else ""
        if not block or not text:
            continue
        base = auto.get(element, 0) or 1
        multi = block.get("lines", 1) >= 2
        if multi:
            want_px = block["font_ratio"] * ref_h / ref_short * min(size.w, size.h)
            scale = want_px / base
            limit = _clamp(block["w"] * size.w / avail, MIN_WIDTH, MAX_WIDTH)
        else:
            at_base = fonts.text_width(text, base, content.lang, bold=element in L.BOLD_ELEMENTS)
            # Không để chữ rộng hơn phần dùng được, nếu không câu ngắn cũng bị ngắt dòng.
            cap = 0.98 * avail / size.w
            target_ratio = min(cap, block["w"] * _boost(ref_w, size.w))
            scale = (target_ratio * size.w / at_base) if at_base > 0 else 1.0
            lo, hi = SCALE_RANGE.get(element, (0.7, 2.0))
            scale = _clamp(scale, lo, hi)
            limit = None
        scale = round(_clamp(scale * shrink, MIN_SCALE, MAX_SCALE), 2)
        px = max(L.MIN_FONT, base * scale)
        width_limit = avail * limit if limit else avail
        _, w, h = fonts.block_size(text, px, content.lang, width_limit,
                                   bold=element in L.BOLD_ELEMENTS)
        items.append({"element": element, "scale": scale, "width": round(limit, 3) if limit else None,
                      "x": _clamp(block["x"], 0, 1) * size.w, "y": _clamp(block["y"], 0, 1) * size.h,
                      "w": w, "h": h})
    return items


def _stack(items: list[dict], size: AdSize, pad: float, gap: float) -> float:
    """Xếp các khối theo thứ tự trên xuống, không khối nào đè khối trên nó.

    Khối nào chạm đáy thì kéo lên vừa đủ, thay vì thu nhỏ chữ của cả cụm — nhờ vậy chữ
    giữ được cỡ như ảnh mẫu mà vẫn nằm trong khung.
    """
    items.sort(key=lambda it: it["y"])
    cursor = pad
    for it in items:
        it["y"] = max(it["y"], cursor)
        it["y"] = min(it["y"], max(cursor, size.h - pad - it["h"]))
        it["x"] = min(max(0.0, it["x"]), max(0.0, size.w - it["w"]))
        cursor = it["y"] + it["h"] + gap
    return cursor - gap


def describe(analysis: dict) -> list[dict]:
    """Mô tả ngắn cho người dùng xem tool đọc được gì từ ảnh."""
    roles = analysis.get("roles") or {}
    out = []
    for element in ROLE_ELEMENTS:
        b = roles.get(element)
        if not b:
            continue
        vertical = "top" if b["y"] < 0.34 else ("bottom" if b["y"] > 0.62 else "middle")
        out.append({"element": element, "align": b["align"], "vertical": vertical,
                    "font_ratio": b["font_ratio"], "color": b["color"]})
    return out
