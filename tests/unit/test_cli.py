import json
import time

import pytest

from html5adbuilder.__main__ import main

CSV = ("headline,description,cta,lang\n"
       "Fast PDF,Open any PDF,Learn more,en\n"
       "빠른 PDF,어떤 PDF도,자세히 보기,ko\n"
       "Đọc PDF nhanh,Mở mọi tệp PDF,Xem chi tiết,vi\n")


@pytest.fixture
def csv_file(tmp_path):
    p = tmp_path / "noi-dung.csv"
    p.write_text(CSV, encoding="utf-8")
    return p


def test_cli_sizes_and_schemes(capsys):
    assert main(["sizes"]) == 0
    assert "300x250" in capsys.readouterr().out
    assert main(["schemes"]) == 0
    assert "Clean White" in capsys.readouterr().out


def test_cli_export(csv_file, tmp_path, capsys):
    rc = main(["export", str(csv_file), str(tmp_path / "out"), "--sizes", "300x250,728x90"])
    out = capsys.readouterr().out
    assert rc == 0 and "6/6 creative" in out
    assert list((tmp_path / "out").glob("creatives_*.zip"))


def test_cli_json_and_badges(csv_file, tmp_path, capsys):
    assert main(["export", str(csv_file), str(tmp_path / "o"), "--sizes", "300x250", "--badge", "free,new",
                 "--json", "--no-zip"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] == 6 and data["zip"] is None


def test_cli_bad_input(tmp_path, capsys):
    assert main(["export", str(tmp_path / "nope.csv"), str(tmp_path / "o")]) == 2
    assert "Lỗi" in capsys.readouterr().err
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b\n1,2\n", encoding="utf-8")
    assert main(["export", str(bad), str(tmp_path / "o")]) == 2


def test_cli_bad_size(csv_file, tmp_path, capsys):
    assert main(["export", str(csv_file), str(tmp_path / "o"), "--sizes", "abc"]) == 2
    assert "300x250" in capsys.readouterr().err


@pytest.mark.integration
def test_speed_3_sets_20_sizes(csv_file, tmp_path, capsys):
    """Yêu cầu phi chức năng: 3 bộ × 20 size dưới 30 giây."""
    sizes = ",".join(s.strip() for s in
                     "300x250,336x280,728x90,300x600,160x600,120x600,970x90,970x250,468x60,250x250,200x200,"
                     "300x1050,320x50,320x100,300x50,320x480,480x320,930x180,980x120,580x400".split(","))
    t0 = time.perf_counter()
    rc = main(["export", str(csv_file), str(tmp_path / "speed"), "--sizes", sizes])
    elapsed = time.perf_counter() - t0
    assert rc == 0 and "60/60 creative" in capsys.readouterr().out
    assert elapsed < 30, f"mất {elapsed:.1f}s"
