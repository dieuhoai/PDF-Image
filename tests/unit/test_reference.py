"""Đọc bố cục từ ảnh mẫu rồi áp sang các kích thước."""
from PIL import Image, ImageDraw

from html5adbuilder import analyze, recipe
from html5adbuilder.models import AdSize, Design


def _ref_image(tmp_path):
    """Ảnh mẫu giống bản khách gửi: tiêu đề to trên-trái, mô tả dưới nó, CTA đỏ ở dưới-phải."""
    img = Image.new("RGB", (1200, 630), (245, 245, 245))
    d = ImageDraw.Draw(img)
    d.rectangle([90, 80, 830, 160], fill=(20, 20, 20))        # tiêu đề
    d.rectangle([92, 220, 700, 252], fill=(90, 90, 90))       # mô tả, dòng 1
    d.rectangle([92, 268, 640, 300], fill=(90, 90, 90))       # mô tả, dòng 2 (ảnh mẫu cố ý ngắt dòng)
    d.rectangle([980, 540, 1120, 580], fill=(232, 52, 26))    # CTA đỏ
    p = tmp_path / "ref.png"
    img.save(p)
    return p


def test_reads_three_blocks_with_positions(tmp_path):
    a = analyze.analyze(_ref_image(tmp_path))
    roles = a["roles"]
    assert set(roles) == {"headline", "description", "cta"}
    assert roles["headline"]["align"] == "left" and roles["headline"]["y"] < 0.2
    assert roles["cta"]["align"] == "right" and roles["cta"]["y"] > 0.8
    assert roles["headline"]["font_ratio"] > roles["description"]["font_ratio"]
    assert roles["cta"]["color"].startswith("#e")       # đỏ


def test_background_and_empty_image(tmp_path):
    blank = tmp_path / "blank.png"
    Image.new("RGB", (200, 200), (255, 255, 255)).save(blank)
    a = analyze.analyze(blank)
    assert a["bg"] == "#ffffff" and a["roles"] == {}


def test_recipe_applies_to_every_size(tmp_path):
    a = analyze.analyze(_ref_image(tmp_path))
    sizes = [AdSize.parse("300x250"), AdSize.parse("728x90")]
    r = recipe.from_analysis(a, sizes, Design())
    assert set(r["positions"]) == {"300x250", "728x90"}
    assert r["layout"] == "left"
    assert r["cta_color"].startswith("#e")
    for key in ("300x250", "728x90"):
        pos = r["positions"][key]
        assert pos["headline"].x < 0.2 and pos["cta"].x > 0.6
        assert pos["cta"].y > pos["headline"].y
        assert 0.4 <= r["scales"][key]["headline"] <= 3.0
        # tiêu đề 1 dòng → không ép bề rộng; mô tả 2 dòng → có ép
        assert "headline" not in r["widths"][key]
        assert 0.15 <= r["widths"][key]["description"] <= 1.0


def test_recipe_handles_image_with_no_text(tmp_path):
    blank = tmp_path / "b.png"
    Image.new("RGB", (100, 100), (250, 250, 250)).save(blank)
    r = recipe.from_analysis(analyze.analyze(blank), [AdSize.parse("300x250")], Design())
    assert r["positions"] == {} and r["cta_color"] == ""


def test_describe_for_humans(tmp_path):
    rows = recipe.describe(analyze.analyze(_ref_image(tmp_path)))
    by = {r["element"]: r for r in rows}
    assert by["headline"]["vertical"] == "top" and by["headline"]["align"] == "left"
    assert by["cta"]["vertical"] == "bottom" and by["cta"]["align"] == "right"


def _ref_like_customer(tmp_path):
    """Giống ảnh khách gửi: tiêu đề to trên-trái, mô tả 1 dòng, CTA đỏ dưới-phải."""
    img = Image.new("RGB", (1920, 1005), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([95, 90, 830, 185], fill=(10, 10, 10))
    d.rectangle([95, 232, 1120, 272], fill=(100, 100, 100))
    d.rectangle([1620, 865, 1810, 915], fill=(240, 60, 30))
    p = tmp_path / "khach.png"
    img.save(p)
    return p


def _content():
    from html5adbuilder.models import ContentSet
    return ContentSet(id="s1", headline="새로운 기능 업데이트!",
                      description="AI 텍스트 인식, 다크 모드, 클라우드 백업이 추가되었습니다.",
                      cta="업데이트", lang="ko")


def test_applied_layout_never_overlaps(tmp_path):
    """Mọi kích thước: chép bố cục xong các khối chữ không được đè lên nhau."""
    from html5adbuilder import layout as L
    from html5adbuilder.models import Creative, Project

    a = analyze.analyze(_ref_like_customer(tmp_path))
    content = _content()
    keys = ["300x250", "336x280", "728x90", "300x600", "160x600", "320x50", "970x250", "320x100"]
    sizes = [AdSize.parse(k) for k in keys]
    design = Design(schemes=["clean_white"], badges=["hot"], cta_style="text")
    plan = recipe.from_analysis(a, sizes, design, [content])
    design = design.model_copy(update={"layout": plan["layout"], "cta_color": plan["cta_color"]})
    project = Project(sets=[content], sizes=sizes, design=design, positions=plan["positions"],
                      scales=plan["scales"], widths=plan["widths"])

    for size in sizes:
        cr = Creative(content=content, size=size, scheme="clean_white", badge="hot")
        lay = L.build(cr, design, project.positions_for("s1", size), project.scales_for("s1", size),
                      project.widths_for("s1", size))
        boxes = lay.boxes
        for i, a_box in enumerate(boxes):
            assert a_box.x >= -0.5 and a_box.y >= -0.5
            assert a_box.x + a_box.w <= size.w + 0.5 and a_box.y + a_box.h <= size.h + 0.5
            for b_box in boxes[i + 1:]:
                overlap = (a_box.x < b_box.x + b_box.w - 1 and b_box.x < a_box.x + a_box.w - 1
                           and a_box.y < b_box.y + b_box.h - 1 and b_box.y < a_box.y + a_box.h - 1)
                assert not overlap, f"{size.key}: {a_box.element} đè {b_box.element}"


def test_headline_keeps_one_line_like_the_reference(tmp_path):
    from html5adbuilder import layout as L
    from html5adbuilder.models import Creative

    a = analyze.analyze(_ref_like_customer(tmp_path))
    content = _content()
    size = AdSize.parse("300x250")
    design = Design(schemes=["clean_white"], cta_style="text")
    plan = recipe.from_analysis(a, [size], design, [content])
    key = f"s1/{size.key}"
    lay = L.build(Creative(content=content, size=size, scheme="clean_white"),
                  design.model_copy(update={"layout": plan["layout"]}),
                  plan["positions"][key], plan["scales"][key], plan["widths"].get(key))
    assert len(lay.box("headline").lines) == 1, lay.box("headline").lines


def test_too_small_canvas_falls_back_to_auto_layout(tmp_path):
    """Khung quá chật thì thà dùng bố cục tự động còn hơn ép theo ảnh mẫu rồi vỡ."""
    a = analyze.analyze(_ref_like_customer(tmp_path))
    plan = recipe.from_analysis(a, [AdSize.parse("120x20")], Design(), [_content()])
    assert "s1/120x20" not in plan["positions"]


def test_small_banner_still_gets_the_layout(tmp_path):
    """320x50 vẫn chép được bố cục — trước đây bị bỏ vì chữ bị co quá đà."""
    a = analyze.analyze(_ref_like_customer(tmp_path))
    plan = recipe.from_analysis(a, [AdSize.parse("320x50")], Design(), [_content()])
    assert "s1/320x50" in plan["positions"]
