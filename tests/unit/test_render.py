import io
import re
import zipfile

import pytest
from PIL import Image

from html5adbuilder import render_html, render_png
from html5adbuilder.models import AdSize, ContentSet, Creative, Design


def _cr(size="300x250", **kw):
    base = {"name": "A", "headline": "Fast PDF", "description": "Open and edit any PDF", "cta": "Learn more",
            "lang": "en"}
    return Creative(content=ContentSet(**{**base, **kw}), size=AdSize.parse(size), scheme="clean_white", badge="new")


def test_html_has_ad_size_and_clicktag_ac4():
    html = render_html.render(_cr(), Design())
    assert '<meta name="ad.size" content="width=300,height=250">' in html
    assert re.search(r"var\s+clickTag\s*=", html)
    assert 'href="javascript:window.open(window.clickTag)"' in html
    assert "<title>" in html and 'lang="en"' in html


def test_html_offline_only_ac4():
    html = render_html.render(_cr(), Design(), click_url="https://example.com/landing?a=1&b=2")
    urls = re.findall(r"https?://[^\"'\s)]+", html)
    assert urls == ["https://example.com/landing?a=1&amp;b=2"], urls
    for bad in ("<script src", "@import", "url(http", "fonts.googleapis"):
        assert bad not in html


def test_html_escapes_content():
    html = render_html.render(_cr(headline='A <b>& "x"', description="5 > 3"), Design())
    assert "<b>" not in html.split("<body")[1]
    assert "&lt;b&gt;" in html and "&amp;" in html and "&gt; 3" in html


def test_html_size_matches_and_is_small():
    for key in ("300x250", "728x90", "320x50", "160x600"):
        html = render_html.render(_cr(key), Design())
        assert f"width:{AdSize.parse(key).w}px" in html.replace(" ", "")
        assert len(html.encode()) < 20_000


def test_html_animation_and_gradient():
    assert "@keyframes adin" in render_html.render(_cr(), Design(animation="fade"))
    # tắt hiệu ứng xuất hiện thì không còn adin; nhịp đập của nút là tuỳ chọn riêng
    assert "@keyframes adin" not in render_html.render(_cr(), Design(animation="none"))
    assert "linear-gradient" in render_html.render(_cr(), Design(gradient="ocean"))
    assert "prefers-reduced-motion" in render_html.render(_cr(), Design(animation="slide"))


def test_html_badge_free_label_per_language():
    cr = _cr(headline="빠른 PDF", cta="자세히 보기", description="", lang="ko").model_copy(update={"badge": "free"})
    html = render_html.render(cr, Design(badges=["free"]))
    assert "무료" in html and 'lang="ko"' in html


def test_html_rtl():
    html = render_html.render(_cr(headline="مرحبا", cta="اعرف المزيد", description="", lang="ar"), Design())
    assert 'dir="rtl"' in html


def test_zip_structure_and_limit_ac4():
    data = render_html.zip_bytes(_cr(), Design())
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.namelist() == ["index.html"]
        assert z.testzip() is None
    assert len(data) <= 150 * 1024


def test_png_exact_pixels_ac9():
    for key in ("300x250", "728x90"):
        img = Image.open(io.BytesIO(render_png.png_bytes(_cr(key), Design())))
        assert img.size == (AdSize.parse(key).w, AdSize.parse(key).h)
        assert img.mode == "RGB"


def test_png_uses_scheme_background():
    img = Image.open(io.BytesIO(render_png.png_bytes(_cr().model_copy(update={"scheme": "dark"}), Design())))
    assert img.getpixel((1, img.height - 2)) == (26, 26, 46)


@pytest.mark.parametrize("lay", ["auto", "center", "left", "top_bottom"])
def test_all_layouts_render(lay):
    assert render_html.render(_cr(), Design(layout=lay)).startswith("<!doctype html>")
    assert render_png.png_bytes(_cr(), Design(layout=lay))


def test_cta_text_style_is_default_and_has_no_pill():
    html = render_html.render(_cr(), Design())
    cta_line = [ln for ln in html.splitlines() if "Learn more" in ln][0]
    assert "background:#1a73e8" not in cta_line and "border-radius" not in cta_line
    assert "color:#1a73e8" in cta_line          # chữ mang màu nhấn của bảng màu

    btn = render_html.render(_cr(), Design(cta_style="button"))
    btn_line = [ln for ln in btn.splitlines() if "Learn more" in ln][0]
    assert "background:#1a73e8" in btn_line and "border-radius" in btn_line


def test_cta_text_style_is_narrower():
    from html5adbuilder import layout as L
    text = L.build(_cr(), Design()).box("cta")
    button = L.build(_cr(), Design(cta_style="button")).box("cta")
    assert text.w < button.w and text.h < button.h


def test_cta_text_style_png_differs():
    a = render_png.png_bytes(_cr(), Design())
    b = render_png.png_bytes(_cr(), Design(cta_style="button"))
    assert a != b


def test_png_scale_gives_bigger_sharper_image():
    one = Image.open(io.BytesIO(render_png.png_bytes(_cr(), Design())))
    three = Image.open(io.BytesIO(render_png.png_bytes(_cr(), Design(), px_scale=3)))
    assert one.size == (300, 250) and three.size == (900, 750)
    # cùng bố cục: nền ở góc vẫn là nền
    assert one.getpixel((2, 2)) == three.getpixel((6, 6))


def test_badge_label_follows_content_language():
    from html5adbuilder import catalog as C
    assert C.badge_label("new", "ko") == "신규" and C.badge_label("new", "vi") == "MỚI"
    assert C.badge_label("hot", "ja") == "人気" and C.badge_label("pro", "ko") == "프로"
    assert C.badge_label("off50", "en") == "50% OFF"
    for badge in C.BADGES:
        for lang in C.LANGUAGES:
            assert C.badge_label(badge, lang), (badge, lang)


def test_animation_runs_in_sequence():
    html = render_html.render(_cr(), Design(animation="fade"))
    delays = sorted(float(d) for d in re.findall(r"animation-delay:([\d.]+)s", html))
    assert len(delays) >= 2 and delays[0] > 0 and delays == sorted(delays)
    assert "animation:adin" in html.replace(" ", "")


def test_no_animation_means_no_delays():
    html = render_html.render(_cr(), Design(animation="none", cta_pulse=False))
    assert "@keyframes" not in html and "animation-delay" not in html


def test_bold_font_covers_each_script():
    """Font đậm phải vẽ được đúng bảng chữ — nếu không chữ ra một dãy ô vuông."""
    from html5adbuilder import fonts
    for lang, sample in (("vi", "ế"), ("ko", "가"), ("ja", "あ"), ("zh", "字"), ("en", "A")):
        face = fonts._bold_face(lang)
        assert face, lang
        f = fonts.font_for(30, bold=True, lang=lang)
        assert fonts._ink(f, sample) != fonts._ink(f, ""), (lang, face)


def test_vietnamese_png_keeps_its_accents():
    cr = _cr(headline="Đọc PDF siêu nhanh", description="Mở và sửa mọi tệp", cta="Xem chi tiết", lang="vi")
    a = render_png.png_bytes(cr, Design())
    b = render_png.png_bytes(_cr(headline="Doc PDF sieu nhanh", description="Mo va sua moi tep",
                                 cta="Xem chi tiet", lang="vi"), Design())
    assert a != b          # có dấu khác không dấu → font vẽ được dấu, không phải ô vuông


def test_cta_pulses_forever():
    """Nút nhấp nháy liên tục như file mẫu khách gửi."""
    html = render_html.render(_cr(), Design(cta_pulse=True))
    assert "@keyframes adpulse" in html and "adpulse 1.8s" in html and "infinite" in html
    assert 'class="el cta"' in html
    assert "@keyframes adpulse" not in render_html.render(_cr(), Design(cta_pulse=False))


def test_fullscreen_format_fits_screen_and_uses_exitapi():
    full = render_html.render(_cr("480x320"), Design(ad_format="fullscreen"), for_export=True)
    assert "exitapi.js" in full and "ExitApi.exit()" in full
    assert "innerWidth/480" in full.replace(" ", "") and "addEventListener('resize'" in full
    assert "<a href=" not in full                      # cả khung bấm được, không cần lớp phủ
    assert 'name="viewport"' in full


def test_banner_format_stays_offline():
    banner = render_html.render(_cr(), Design(), for_export=True)
    assert "googlesyndication" not in banner and "ExitApi" not in banner
    urls = re.findall(r"https?://[^\"'\s)]+", banner)
    assert urls == ["https://www.google.com"]


def test_preview_does_not_load_the_exit_script():
    """Bản xem trước trong app chạy offline nên không nhúng script của Google."""
    preview = render_html.render(_cr("480x320"), Design(ad_format="fullscreen"))
    assert "googlesyndication" not in preview


def test_fullscreen_has_no_border_and_is_clickable():
    full = render_html.render(_cr("480x320"), Design(ad_format="fullscreen"), for_export=True)
    assert "cursor:pointer" in full and "border:1px solid" not in full
    assert "border:1px solid" in render_html.render(_cr(), Design())
