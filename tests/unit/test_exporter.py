import json
import zipfile

import pytest

from html5adbuilder import exporter
from html5adbuilder.models import AdSize, ContentSet, Design, ExportOptions, ExportRequest, Pos, Project


def _project(**kw):
    sets = [ContentSet(id="s1", name="Bộ Hàn 🎯", headline="빠른 PDF", description="어떤 PDF도", cta="자세히 보기",
                       lang="ko"),
            ContentSet(id="s2", name="EN", headline="Fast PDF", description="Open any PDF", cta="Learn more",
                       lang="en")]
    base = {"sets": sets, "sizes": [AdSize(w=300, h=250), AdSize(w=728, h=90)],
            "design": Design(schemes=["clean_white"], badges=["new"]),
            "export": ExportOptions(png=False)}
    return Project(**{**base, **kw})


def _run(tmp_path, project=None, **cb):
    req = ExportRequest(project=project or _project(), output_dir=tmp_path)
    return exporter.export(req, **cb)


def test_export_creates_folder_and_zips_ac6(tmp_path):
    res = _run(tmp_path)
    assert res.ok_count == 4 and not res.failed
    folder = res.folder
    assert folder.name.startswith("creatives_") and folder.parent == tmp_path
    files = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*.zip"))
    assert files == ["Bo-Han/300x250.zip", "Bo-Han/728x90.zip", "EN/300x250.zip", "EN/728x90.zip"]
    with zipfile.ZipFile(folder / "EN" / "300x250.zip") as z:
        assert z.namelist() == ["index.html"]
        assert b"ad.size" in z.read("index.html")


def test_group_by_size_and_flat_ac6(tmp_path):
    folder = _run(tmp_path, _project(export=ExportOptions(group_by="size"))).folder
    files = sorted(x.relative_to(folder).as_posix() for x in folder.rglob("*.zip"))
    assert files == ["300x250/Bo-Han.zip", "300x250/EN.zip", "728x90/Bo-Han.zip", "728x90/EN.zip"]
    p2 = _project(export=ExportOptions(group_by="flat"))
    res = _run(tmp_path / "b", p2)
    assert sorted(x.name for x in res.folder.rglob("*.zip")) == ["Bo-Han_300x250.zip", "Bo-Han_728x90.zip",
                                                                 "EN_300x250.zip", "EN_728x90.zip"]


def test_manifest_ac7(tmp_path):
    res = _run(tmp_path)
    data = json.loads((res.folder / "manifest.json").read_text(encoding="utf-8"))
    assert data["count"] == 4 and data["generator"].startswith("HTML5 Ad Builder")
    item = data["creatives"][0]
    assert {"file", "set", "size", "scheme", "badge", "lang", "bytes", "headline"} <= set(item)
    assert item["bytes"] > 0 and item["size"] == "300x250"


def test_preview_page_ac8(tmp_path):
    html = (_run(tmp_path).folder / "preview" / "index.html").read_text(encoding="utf-8")
    assert html.count("<iframe") == 4 and "300x250" in html
    assert "Bộ Hàn" in html  # tên gốc hiển thị, kể cả khi tên file đã bỏ dấu


def test_png_option_ac9(tmp_path):
    res = _run(tmp_path, _project(export=ExportOptions(png=True, group_by="flat")))
    pngs = sorted(p.name for p in res.folder.rglob("*.png"))
    assert pngs == ["Bo-Han_300x250.png", "Bo-Han_728x90.png", "EN_300x250.png", "EN_728x90.png"]


def test_zip_all_and_unique_folder(tmp_path):
    res = _run(tmp_path)
    assert res.zip_path and res.zip_path.exists() and res.zip_path.suffix == ".zip"
    with zipfile.ZipFile(res.zip_path) as z:
        assert any(n.endswith("manifest.json") for n in z.namelist())
    again = _run(tmp_path)
    assert again.folder != res.folder and again.folder.name.endswith("-2")


def test_positions_applied(tmp_path):
    p = _project(positions={"300x250": {"headline": Pos(x=0.0, y=0.0)}})
    folder = _run(tmp_path, p).folder
    with zipfile.ZipFile(folder / "EN" / "300x250.zip") as z:
        html = z.read("index.html").decode()
    assert "left:0.0px;top:0.0px" in html.replace(" ", "")


def test_one_bad_item_does_not_stop_ac13(tmp_path, monkeypatch):
    calls = {"n": 0}
    real = exporter.render_html.zip_bytes

    def flaky(cr, *a, **k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise ValueError("giả lập lỗi")
        return real(cr, *a, **k)

    monkeypatch.setattr(exporter.render_html, "zip_bytes", flaky)
    res = _run(tmp_path)
    assert res.ok_count == 3 and len(res.failed) == 1 and "giả lập lỗi" in res.failed[0].error
    assert (res.folder / "report.csv").read_text(encoding="utf-8").count("\n") == 5


def test_stop_midway_ac14(tmp_path):
    seen = []
    res = _run(tmp_path, on_progress=lambda d, t, it: seen.append(d), should_stop=lambda: len(seen) >= 2)
    assert len(res.items) == 2 and res.folder.exists()


def test_progress_reports_total(tmp_path):
    seen = []
    _run(tmp_path, on_progress=lambda d, t, it: seen.append((d, t)))
    assert seen[0][1] == 4 and [d for d, _ in seen] == [1, 2, 3, 4]


def test_warning_for_overflowing_size(tmp_path):
    p = _project(sizes=[AdSize(w=70, h=14)])
    res = _run(tmp_path, p)
    assert any(i.warnings for i in res.items)


def test_rejects_empty_project(tmp_path):
    with pytest.raises(ValueError, match="bộ nội dung"):
        ExportRequest(project=Project(sets=[]), output_dir=tmp_path)


def test_scales_applied_and_validated(tmp_path):
    content = _project().sets[0]
    p = _project(scales={"300x250": {"headline": 1.8}})
    folder = _run(tmp_path, p).folder
    with zipfile.ZipFile(folder / "Bo-Han" / "300x250.zip") as z:
        big = z.read("index.html").decode()
    plain_folder = _run(tmp_path / "b", _project()).folder
    with zipfile.ZipFile(plain_folder / "Bo-Han" / "300x250.zip") as z:
        plain = z.read("index.html").decode()
    assert big != plain
    assert p.scales_for(content.id, AdSize(w=300, h=250)) == {"headline": 1.8}
    with pytest.raises(ValueError, match="0.4"):
        Project(sets=[content], scales={"300x250": {"headline": 9.0}})


def test_widths_reach_the_exported_file(tmp_path):
    content = _project().sets[0]
    p = _project(widths={"300x250": {"headline": 0.5}})
    folder = _run(tmp_path, p).folder
    with zipfile.ZipFile(folder / "Bo-Han" / "300x250.zip") as z:
        narrow = z.read("index.html").decode()
    plain_folder = _run(tmp_path / "b", _project()).folder
    with zipfile.ZipFile(plain_folder / "Bo-Han" / "300x250.zip") as z:
        plain = z.read("index.html").decode()
    assert narrow != plain
    assert p.widths_for(content.id, AdSize(w=300, h=250)) == {"headline": 0.5}
    with pytest.raises(ValueError, match="bề rộng"):
        Project(sets=[content], widths={"300x250": {"cta": 0.5}})


def test_excluded_creatives_are_not_exported(tmp_path):
    p = _project()
    skipped = list(p.all_creatives())[0]
    p = _project(excluded=[skipped.key])
    assert p.creative_count == 3
    res = _run(tmp_path, p)
    assert res.ok_count == 3
    names = sorted(x.name for x in res.folder.rglob("*.zip"))
    assert len(names) == 3
    data = json.loads((res.folder / "manifest.json").read_text(encoding="utf-8"))
    assert data["count"] == 3


def test_excluding_everything_is_refused(tmp_path):
    p = _project(excluded=[c.key for c in _project().all_creatives()])
    with pytest.raises(ValueError, match="bỏ hết"):
        ExportRequest(project=p, output_dir=tmp_path)


def test_png_only_export(tmp_path):
    res = _run(tmp_path, _project(export=ExportOptions(html=False, png=True, group_by="flat")))
    files = sorted(p.name for p in res.folder.rglob("*") if p.suffix in (".zip", ".png"))
    assert files == ["Bo-Han_300x250.png", "Bo-Han_728x90.png", "EN_300x250.png", "EN_728x90.png"]
    data = json.loads((res.folder / "manifest.json").read_text(encoding="utf-8"))
    assert data["creatives"][0]["file"].endswith(".png") and data["creatives"][0]["bytes"] > 0
    page = (res.folder / "preview" / "index.html").read_text(encoding="utf-8")
    assert page.count("<img") == 4 and "<iframe" not in page


def test_html_and_png_together(tmp_path):
    res = _run(tmp_path, _project(export=ExportOptions(html=True, png=True, group_by="flat")))
    assert len(list(res.folder.rglob("*.zip"))) == 4
    assert len(list(res.folder.rglob("*.png"))) == 4
    assert res.items[0].name.endswith(".zip")


def test_no_format_chosen_is_refused():
    with pytest.raises(ValueError, match="ít nhất một định dạng"):
        ExportOptions(html=False, png=False)


def test_html_and_png_go_to_separate_folders(tmp_path):
    """Xuất cả hai định dạng thì file .zip và ảnh nằm hai thư mục riêng."""
    res = _run(tmp_path, _project(export=ExportOptions(html=True, png=True, group_by="set")))
    folder = res.folder
    zips = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*.zip"))
    pngs = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*.png"))
    assert zips == ["html5/Bo-Han/300x250.zip", "html5/Bo-Han/728x90.zip",
                    "html5/EN/300x250.zip", "html5/EN/728x90.zip"]
    assert pngs == ["images/Bo-Han/300x250.png", "images/Bo-Han/728x90.png",
                    "images/EN/300x250.png", "images/EN/728x90.png"]
    data = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert data["creatives"][0]["file"].startswith("html5/")
    assert data["creatives"][0]["png"].startswith("images/")


def test_single_format_keeps_flat_folders(tmp_path):
    res = _run(tmp_path, _project(export=ExportOptions(html=True, png=False)))
    assert not (res.folder / "html5").exists()
    assert (res.folder / "Bo-Han" / "300x250.zip").exists()


def test_warns_about_png_for_complex_scripts(tmp_path):
    """Tiếng Thái/Ả Rập/Hindi: ảnh PNG có thể sai dấu — phải nói trước cho người dùng."""
    from html5adbuilder import fonts
    thai = ContentSet(id="t1", name="TH", headline="อ่าน PDF เร็ว", description="เปิดไฟล์ได้ทันที",
                      cta="ดูรายละเอียด", lang="th")
    p = Project(sets=[thai], sizes=[AdSize(w=300, h=250)], export=ExportOptions(png=True))
    res = _run(tmp_path, p)
    if fonts.shapes_complex_text():
        assert not any("sai dấu" in w for i in res.items for w in i.warnings)
    else:
        assert any("sai dấu" in w for i in res.items for w in i.warnings), res.items[0].warnings
    assert res.ok_count == 1      # vẫn xuất được, chỉ là có cảnh báo
