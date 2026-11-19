import io

from PIL import Image

from html5adbuilder import csv_import, palette


def test_csv_basic_ac11(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("headline,description,cta,lang\nFast PDF,Open any PDF,Learn more,en\n"
                 "빠른 PDF,어떤 PDF도,자세히 보기,ko\n", encoding="utf-8")
    sets, errors = csv_import.load(p)
    assert errors == [] and len(sets) == 2
    assert sets[1].lang == "ko" and sets[1].cta == "자세히 보기"


def test_csv_bom_semicolon_and_aliases(tmp_path):
    p = tmp_path / "b.csv"
    p.write_text("﻿Tên bộ;Headline;Mô tả;CTA;Ngôn ngữ\nBộ 1;Đọc PDF nhanh;Mở mọi PDF;Xem chi tiết;vi\n",
                 encoding="utf-8")
    sets, errors = csv_import.load(p)
    assert errors == [] and sets[0].name == "Bộ 1" and sets[0].lang == "vi"


def test_csv_bad_rows_listed_not_fatal_ac11(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("headline,cta,lang\n" + "x" * 30 + ",Learn more,en\nOK one,Learn more,zz\nGood,Learn more,en\n",
                 encoding="utf-8")
    sets, errors = csv_import.load(p)
    assert len(sets) == 1 and sets[0].headline == "Good"
    assert len(errors) == 2 and errors[0].startswith("Dòng 2")
    assert "20 ký tự" in errors[0] and "zz" in errors[1]


def test_csv_missing_column(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("foo,bar\n1,2\n", encoding="utf-8")
    sets, errors = csv_import.load(p)
    assert sets == [] and "headline" in errors[0].lower()


def test_csv_latin1_fallback(tmp_path):
    p = tmp_path / "e.csv"
    p.write_bytes("headline,cta,lang\nCafé PDF,Learn more,fr\n".encode("latin-1"))
    sets, errors = csv_import.load(p)
    assert errors == [] and sets[0].headline == "Café PDF"


def _img(color, tmp_path, name="x.png"):
    p = tmp_path / name
    Image.new("RGB", (64, 64), color).save(p)
    return p


def test_palette_suggest_blue_ac12(tmp_path):
    s = palette.suggest(_img((26, 115, 232), tmp_path))
    assert s["scheme"] == "blue_trust"
    assert 0 <= s["confidence"] <= 1 and s["dominant"].startswith("#")


def test_palette_suggest_dark_and_white(tmp_path):
    assert palette.suggest(_img((18, 18, 30), tmp_path, "d.png"))["scheme"] == "dark"
    assert palette.suggest(_img((252, 252, 252), tmp_path, "w.png"))["scheme"] in ("clean_white", "soft_gray")
    assert palette.suggest(_img((40, 140, 70), tmp_path, "g.png"))["scheme"] == "green_fresh"


def test_palette_from_bytes_and_bad_file(tmp_path):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (255, 240, 220)).save(buf, "PNG")
    assert palette.suggest_bytes(buf.getvalue())["scheme"] == "warm_cream"
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not an image")
    try:
        palette.suggest(bad)
        raise AssertionError("phải báo lỗi")
    except ValueError as e:
        assert "ảnh" in str(e).lower()


def test_palette_suggests_accent_colour_for_cta(tmp_path):
    img = Image.new("RGB", (64, 64), (250, 250, 250))
    for x in range(10, 54):          # một khối đỏ như logo trong ảnh tham chiếu
        for y in range(10, 54):
            img.putpixel((x, y), (200, 30, 40))
    p = tmp_path / "logo.png"
    img.save(p)
    s = palette.suggest(p)
    assert s["accent"] and s["accent"].startswith("#")
    r, g, b = (int(s["accent"][i:i + 2], 16) for i in (1, 3, 5))
    assert r > g + 60 and r > b + 60, s["accent"]


def test_palette_accent_none_for_flat_grey(tmp_path):
    p = tmp_path / "grey.png"
    Image.new("RGB", (32, 32), (180, 180, 180)).save(p)
    assert palette.suggest(p)["accent"] is None
