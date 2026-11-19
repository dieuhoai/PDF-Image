from html5adbuilder import fonts, layout
from html5adbuilder.models import AdSize, ContentSet, Creative, Design, Pos, Project


def _cr(size="300x250", **kw):
    base = {"name": "A", "headline": "Fast PDF", "description": "Open and edit any PDF quickly", "cta": "Learn more",
            "lang": "en"}
    return Creative(content=ContentSet(**{**base, **kw}), size=AdSize.parse(size), scheme="clean_white", badge="new")


def test_font_measure_scales_with_size():
    narrow = fonts.text_width("Hello world", 12, "en")
    wide = fonts.text_width("Hello world", 24, "en")
    assert 0 < narrow < wide
    assert fonts.text_width("", 12, "en") == 0
    # CJK rộng hơn Latin cùng số ký tự
    assert fonts.text_width("빠른 리더", 20, "ko") > fonts.text_width("fast r", 20, "en")


def test_wrap_by_words_and_by_char():
    lines = fonts.wrap("Open and edit any PDF quickly", 14, "en", 120)
    assert len(lines) > 1 and all(fonts.text_width(ln, 14, "en") <= 120 for ln in lines)
    assert " ".join(lines).split() == "Open and edit any PDF quickly".split()
    # tiếng Nhật không có khoảng trắng → cắt theo ký tự
    jp = fonts.wrap("どんなPDFもすばやく開いて編集できます", 14, "ja", 100)
    assert len(jp) > 1 and "".join(jp) == "どんなPDFもすばやく開いて編集できます"


def test_layout_fits_inside_canvas():
    for key in ("300x250", "728x90", "320x50", "160x600", "970x250", "120x600"):
        lay = layout.build(_cr(key), Design())
        for b in lay.boxes:
            assert b.x >= 0 and b.y >= 0, (key, b.element)
            assert b.x + b.w <= lay.size.w + 0.5, (key, b.element, b.w)
            assert b.y + b.h <= lay.size.h + 0.5, (key, b.element, b.h)
        assert {b.element for b in lay.boxes} >= {"headline", "cta"}


def test_small_size_shrinks_font_ac5():
    big = layout.build(_cr("300x250"), Design())
    small = layout.build(_cr("320x50"), Design())
    assert small.box("headline").font_size < big.box("headline").font_size
    assert small.box("headline").font_size >= layout.MIN_FONT


def test_overflow_warning_ac5():
    long_hl = _cr("320x50", headline="Xin chào bạn nhé ok", description="", lang="vi")
    tiny = layout.build(long_hl.model_copy(update={"size": AdSize(w=120, h=20)}), Design())
    assert any("120x20" in w for w in tiny.warnings), tiny.warnings
    assert not layout.build(_cr("300x250"), Design()).warnings


def test_badge_only_when_requested():
    assert layout.build(_cr(), Design(badges=["new"])).box("badge") is not None
    plain = layout.build(_cr().model_copy(update={"badge": None}), Design())
    assert plain.box("badge") is None


def test_position_override_ac10():
    pos = {"headline": Pos(x=0.5, y=0.5)}
    lay = layout.build(_cr(), Design(), positions=pos)
    # x bị kéo lại vài pixel khi khối rộng hơn nửa khung — đó là chặn không cho tràn
    assert abs(lay.box("headline").x - 150) < 3 and abs(lay.box("headline").y - 125) < 1
    # không cho trôi ra ngoài khung
    edge = layout.build(_cr(), Design(), positions={"cta": Pos(x=1.0, y=1.0)})
    assert edge.box("cta").x + edge.box("cta").w <= 300.5


def test_project_positions_precedence_ac10():
    content = _cr().content
    p = Project(sets=[content], sizes=[AdSize(w=300, h=250)],
                positions={"300x250": {"headline": Pos(x=0.1, y=0.1), "cta": Pos(x=0.2, y=0.8)},
                           f"{content.id}/300x250": {"headline": Pos(x=0.6, y=0.6)}})
    merged = p.positions_for(content.id, AdSize(w=300, h=250))
    assert merged["headline"].x == 0.6 and merged["cta"].x == 0.2


def test_rtl_and_align():
    ar = layout.build(_cr(headline="مرحبا", cta="اعرف المزيد", description="", lang="ar"), Design(layout="left"))
    assert ar.rtl is True
    assert layout.build(_cr(), Design(layout="left")).rtl is False


def test_font_scale_per_element():
    big = layout.build(_cr(), Design(), scales={"headline": 1.6})
    normal = layout.build(_cr(), Design())
    assert big.box("headline").font_size > normal.box("headline").font_size
    # chỉnh headline không làm đổi cỡ các thành phần khác
    assert big.box("cta").font_size == normal.box("cta").font_size
    assert big.box("description").font_size == normal.box("description").font_size
    small = layout.build(_cr(), Design(), scales={"cta": 0.6})
    assert small.box("cta").font_size < normal.box("cta").font_size


def test_font_scale_stays_inside_canvas():
    lay = layout.build(_cr("320x50"), Design(), scales={"headline": 3.0, "cta": 3.0})
    for b in lay.boxes:
        assert b.x + b.w <= lay.size.w + 0.5 and b.y + b.h <= lay.size.h + 0.5


def test_box_width_override_changes_wrapping():
    wide = layout.build(_cr(), Design())
    narrow = layout.build(_cr(), Design(), widths={"headline": 0.4})
    assert narrow.box("headline").w < wide.box("headline").w
    assert len(narrow.box("headline").lines) >= len(wide.box("headline").lines)
    for b in narrow.boxes:
        assert b.x + b.w <= narrow.size.w + 0.5


def test_box_width_only_affects_its_element():
    base = layout.build(_cr(), Design())
    narrow = layout.build(_cr(), Design(), widths={"description": 0.5})
    assert narrow.box("headline").w == base.box("headline").w
    assert narrow.box("description").w < base.box("description").w


def test_badge_moves_away_when_text_sits_in_its_corner():
    """Chữ kéo lên góc trên-trái thì nhãn góc phải tự né, không đè lên chữ."""
    pos = {"headline": Pos(x=0.02, y=0.02)}
    lay = layout.build(_cr(), Design(badges=["new"]), positions=pos)
    badge, head = lay.box("badge"), lay.box("headline")
    assert not (badge.x < head.x + head.w and head.x < badge.x + badge.w
                and badge.y < head.y + head.h and head.y < badge.y + badge.h), (badge, head)
    assert badge.x + badge.w <= lay.size.w + 0.5 and badge.y + badge.h <= lay.size.h + 0.5


def test_badge_stays_where_the_user_dragged_it():
    pos = {"badge": Pos(x=0.4, y=0.4)}
    lay = layout.build(_cr(), Design(badges=["new"]), positions=pos)
    assert abs(lay.box("badge").x - 120) < 1 and abs(lay.box("badge").y - 100) < 1
