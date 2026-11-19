"""Sinh file HTML5 một mình một gói (self-contained) đúng chuẩn Google Ads.

Bắt buộc có: `<meta name="ad.size">`, biến `clickTag`, không tải tài nguyên từ ngoài.
Mỗi dòng chữ đã được tính sẵn ở `layout.py` nên in ra với `white-space: nowrap` — trình duyệt
không cần tự xuống dòng, bản HTML và bản PNG giống nhau.
"""
from __future__ import annotations

import io
import zipfile
from html import escape

from . import catalog as C
from . import layout as L
from .models import Creative, Design, Pos

# Font stack: chỉ font có sẵn trên máy người xem, không tải từ mạng.
FONT_STACK = ("Arial, 'Helvetica Neue', Helvetica, 'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', "
              "'Hiragino Sans', 'Noto Sans', sans-serif")

_ANIM = {
    "fade": "from{opacity:0}to{opacity:1}",
    "slide": "from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}",
    "scale": "from{opacity:0;transform:scale(.94)}to{opacity:1;transform:none}",
}


def _luma(hex_color: str) -> float:
    """Độ sáng cảm nhận được (0–1), dùng để chọn chữ đen hay trắng cho dễ đọc."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def colors(scheme: str, gradient: str, cta_color: str = "") -> dict[str, str]:
    base = dict(C.SCHEMES[scheme])
    if gradient != "none":
        g = C.GRADIENTS[gradient]
        base.update(C.GRADIENT_COLORS)
        base["bg"] = f"linear-gradient(135deg,{g['from']},{g['to']})"
    if cta_color:
        base["cta_bg"] = cta_color
        base["cta_text"] = "#1a1a1a" if _luma(cta_color) > 0.6 else "#ffffff"
    return base


# Các khối hiện lần lượt, cách nhau ngần này giây — nhìn ra hiệu ứng rõ hơn hiện cùng lúc.
STAGGER = 0.18


def _text_div(b: L.Box, color: str, weight: int, extra: str = "", order: int = 0,
              css_class: str = "") -> str:
    lines = "".join(f'<div class="ln">{escape(ln)}</div>' for ln in b.lines)
    delay = f"animation-delay:{round(order * STAGGER, 2)}s;" if order else ""
    classes = f"el {css_class}".strip()
    return (f'<div class="{classes}" style="left:{b.x}px;top:{b.y}px;width:{b.w}px;height:{b.h}px;'
            f'font-size:{b.font_size}px;line-height:{round(b.font_size * 1.25, 2)}px;color:{color};'
            f'font-weight:{weight};text-align:{b.align};{delay}{extra}">{lines}</div>')


FIT_SCRIPT = """(function(){var a=document.getElementById('ad');function f(){\
var s=Math.min(innerWidth/%(w)d,innerHeight/%(h)d);a.style.transform='scale('+s+')';\
a.style.left=((innerWidth-%(w)d*s)/2)+'px';a.style.top=((innerHeight-%(h)d*s)/2)+'px';}\
addEventListener('resize',f);f();a.addEventListener('click',function(){\
if(window.ExitApi&&ExitApi.exit){ExitApi.exit();}else{open(window.clickTag,'_blank');}});})();"""


def render(cr: Creative, design: Design, click_url: str = "https://www.google.com",
           positions: dict[str, Pos] | None = None, animate: bool = True,
           scales: dict[str, float] | None = None, widths: dict[str, float] | None = None,
           for_export: bool = False) -> str:
    """Trả về toàn bộ nội dung `index.html` của một creative.

    `animate=False` dùng cho lưới xem trước trong app: bỏ hiệu ứng xuất hiện để mọi ô
    hiện ngay ở trạng thái cuối, nhìn và kéo thả cho dễ.
    """
    lay = L.build(cr, design, positions, scales, widths)
    col = colors(cr.scheme, design.gradient, design.cta_color)
    size, lang = cr.size, cr.content.lang
    rtl = ' dir="rtl"' if lay.rtl else ""

    anim = _ANIM.get(design.animation) if animate else None
    stagger = 1 if anim else 0          # không có hiệu ứng thì khỏi ghi độ trễ vào từng khối

    parts: list[str] = []
    hl = lay.box("headline")
    if hl:
        parts.append(_text_div(hl, col["text"], 800, order=0))
    desc = lay.box("description")
    if desc:
        parts.append(_text_div(desc, col["sub"], 400, order=1 * stagger))
    bd = lay.box("badge")
    if bd:
        bb = C.BADGES[cr.badge or "new"]
        parts.append(_text_div(bd, bb["text"], 700,
                               f'background:{bb["bg"]};border-radius:{round(bd.h / 2, 1)}px;'
                               f'display:flex;align-items:center;justify-content:center', order=3 * stagger))
    cta = lay.box("cta")
    if cta:
        style = (f'background:{col["cta_bg"]};border-radius:{min(6, round(cta.h / 4, 1))}px;'
                 'display:flex;align-items:center;justify-content:center') if design.cta_style == "button" \
            else 'display:flex;align-items:center;justify-content:center'
        color = col["cta_text"] if design.cta_style == "button" else col["cta_bg"]
        parts.append(_text_div(cta, color, 800, style, order=2 * stagger, css_class="cta"))

    anim_css = ""
    if anim:
        anim_css = f"@keyframes adin{{{anim}}}#ad>.el{{animation:adin .55s ease-out both}}"
    if design.cta_pulse and animate:
        # Nút đập nhẹ liên tục cho bắt mắt; bắt đầu sau khi các khối đã hiện xong.
        delay = round(3 * STAGGER + 0.6, 2)
        anim_css += ("@keyframes adpulse{0%,100%{transform:scale(1)}50%{transform:scale(1.07)}}"
                     f"#ad>.cta{{animation:{'adin .55s ease-out both,' if anim else ''}"
                     f"adpulse 1.8s {delay}s infinite}}")
    if anim_css:
        anim_css += "@media(prefers-reduced-motion:reduce){#ad>.el{animation:none;opacity:1;transform:none}}"

    # Toàn màn hình thì bỏ viền (quảng cáo chiếm trọn màn hình) và để con trỏ bàn tay vì bấm đâu cũng được.
    frame = "cursor:pointer;" if design.ad_format == "fullscreen" else f"border:1px solid {col['border']};"
    css = (
        f"html,body{{margin:0;padding:0;background:transparent;width:100%;height:100%;overflow:hidden}}"
        f"#ad{{position:absolute;top:0;left:0;transform-origin:top left;"
        f"width:{size.w}px;height:{size.h}px;overflow:hidden;background:{col['bg']};"
        f"{frame}box-sizing:border-box;font-family:{FONT_STACK};"
        f"-webkit-font-smoothing:antialiased}}"
        f"#ad a{{position:absolute;inset:0;display:block;text-decoration:none;z-index:9}}"
        f".el{{position:absolute;box-sizing:border-box;white-space:nowrap;overflow:hidden}}"
        f".ln{{white-space:nowrap}}"
        f"{anim_css}"
    )
    title = escape(cr.content.label)[:60] or "Ad"
    full = design.ad_format == "fullscreen"
    # Toàn màn hình: quảng cáo tự co cho vừa màn hình điện thoại, bấm chỗ nào cũng mở link
    # qua ExitApi của Google (mạng quảng cáo yêu cầu vậy ở định dạng này).
    head_extra = f'<script src="{C.EXIT_API_URL}"></script>\n' if (full and for_export) else ""
    viewport = ('<meta name="viewport" content="width=device-width,initial-scale=1,'
                'maximum-scale=1,user-scalable=no">\n') if full else ""
    if full:
        click_layer = ""
        tail = ("<script>" + FIT_SCRIPT % {"w": size.w, "h": size.h} + "</script>\n")
    else:
        click_layer = (f'<a href="javascript:window.open(window.clickTag)" target="_blank" '
                       f'aria-label="{title}"></a>\n')
        tail = ""
    return (
        "<!doctype html>\n"
        f'<html lang="{escape(lang)}"{rtl}>\n<head>\n<meta charset="utf-8">\n'
        f"{viewport}"
        f'<meta name="ad.size" content="width={size.w},height={size.h}">\n'
        f"<title>{title} {size.key}</title>\n"
        f"{head_extra}"
        f"<style>{css}</style>\n</head>\n<body>\n"
        f'<div id="ad">\n' + "\n".join(parts) + "\n"
        f"{click_layer}"
        "</div>\n"
        f'<script>var clickTag = "{escape(click_url, quote=True)}";</script>\n'
        f"{tail}"
        "</body>\n</html>\n"
    )


def zip_bytes(cr: Creative, design: Design, click_url: str = "https://www.google.com",
              positions: dict[str, Pos] | None = None, scales: dict[str, float] | None = None,
              widths: dict[str, float] | None = None) -> bytes:
    """Gói `index.html` thành ZIP đúng dạng Google Ads nhận."""
    html = render(cr, design, click_url, positions, True, scales, widths, for_export=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        info = zipfile.ZipInfo("index.html", date_time=(2020, 1, 1, 0, 0, 0))  # cố định để file lặp lại được
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, html.encode("utf-8"))
    data = buf.getvalue()
    if len(data) > C.MAX_ZIP_BYTES:
        raise ValueError(f"ZIP {len(data) // 1024} KB vượt giới hạn {C.MAX_ZIP_BYTES // 1024} KB của Google Ads")
    return data
