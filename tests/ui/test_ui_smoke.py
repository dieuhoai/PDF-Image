"""Test giao diện bằng Playwright: đi hết 4 bước, xuất thật, không lỗi JS, không tràn ngang."""
import socket
import threading
import time

import pytest

pw = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.ui

TOKEN = "ui-test"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server():
    import uvicorn

    from web.server import create_app
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(create_app(TOKEN, {f"127.0.0.1:{port}"}), host="127.0.0.1", port=port,
                                        log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    th.join(5)


@pytest.fixture
def page(server):
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chưa cài Chromium: {e}")
        pg = browser.new_page(viewport={"width": 1440, "height": 900})
        pg.errors = []
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        pg.goto(f"{server}/?t={TOKEN}")
        pg.wait_for_selector("[data-testid='headline']")
        yield pg
        browser.close()


def _add_set(page, headline="Đọc PDF siêu nhanh", desc="Mở mọi tệp PDF", cta="Xem chi tiết"):
    page.get_by_test_id("headline").fill(headline)
    page.get_by_test_id("description").fill(desc)
    page.get_by_test_id("cta").fill(cta)
    page.get_by_test_id("add-set").click()


def test_full_flow_exports(page, tmp_path):
    _add_set(page)
    pw.expect(page.get_by_test_id("set-list")).to_contain_text("Đọc PDF siêu nhanh")

    page.get_by_test_id("step-2").click()
    pw.expect(page.get_by_test_id("total")).to_contain_text("6")
    page.get_by_test_id("scheme-dark").click()
    pw.expect(page.get_by_test_id("total")).to_contain_text("12")

    # Chữ dài bị xuống dòng nên so từng dòng, không so cả câu.
    frame = page.frame_locator("[data-testid='live-preview']")
    pw.expect(frame.locator("#ad")).to_contain_text("Mở mọi tệp PDF")
    pw.expect(frame.locator("#ad")).to_contain_text("Xem chi tiết")

    page.get_by_test_id("step-4").click()
    out = tmp_path / "ket-qua"
    out.mkdir()
    page.get_by_test_id("output-dir").fill(str(out))
    page.get_by_test_id("run").click()
    pw.expect(page.get_by_test_id("status")).to_contain_text("12/12", timeout=30_000)
    pw.expect(page.get_by_test_id("status")).to_contain_text("Hoàn tất", timeout=10_000)

    assert len(list(out.rglob("*.zip"))) >= 12
    assert not page.errors, page.errors


def test_cta_warning_and_limits(page):
    page.get_by_test_id("cta").fill("Tải xuống ngay")
    pw.expect(page.get_by_test_id("cta-warn")).to_contain_text("tải xuống")
    page.get_by_test_id("cta").fill("Xem chi tiết")
    pw.expect(page.get_by_test_id("cta-ok")).to_be_visible()
    page.get_by_test_id("headline").fill("x" * 40)
    assert len(page.get_by_test_id("headline").input_value()) == 20


def test_custom_size_and_errors(page):
    _add_set(page)
    page.get_by_test_id("step-2").click()
    page.locator("input[aria-label='Kích thước tự nhập']").fill("abc")
    page.get_by_test_id("add-size").click()
    pw.expect(page.get_by_test_id("error")).to_contain_text("RỘNGxCAO")
    page.locator("input[aria-label='Kích thước tự nhập']").fill("400x400")
    page.get_by_test_id("add-size").click()
    pw.expect(page.get_by_test_id("size-grid")).to_contain_text("400x400")


def test_mobile_width_has_no_horizontal_scroll(server):
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Chưa cài Chromium: {e}")
        pg = browser.new_page(viewport={"width": 375, "height": 812})
        errors: list[str] = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(f"{server}/?t={TOKEN}")
        pg.wait_for_selector("[data-testid='headline']")
        _add_set(pg)
        for step in ("step-2", "step-3", "step-4"):
            pg.get_by_test_id(step).click()
            pg.wait_for_timeout(400)
            assert pg.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"tràn ngang ở {step}"
        browser.close()
        assert not errors, errors


def test_dark_mode(page):
    page.evaluate("document.documentElement.dataset.theme = 'dark'")
    assert page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(11, 11, 20)"
    assert not page.errors, page.errors


def test_design_change_updates_preview_immediately(page):
    _add_set(page)
    page.get_by_test_id("step-2").click()
    frame = page.frame_locator("[data-testid='live-preview']")
    pw.expect(frame.locator("#ad")).to_contain_text("Xem chi tiết")
    page.get_by_test_id("badge-free").click()
    pw.expect(frame.locator("#ad")).to_contain_text("MIỄN PHÍ", timeout=5_000)
    page.get_by_test_id("scheme-dark").click()
    pw.expect(frame.locator("#ad")).to_contain_text("MIỄN PHÍ")
    assert not page.errors, page.errors


def test_grid_shows_every_creative_and_filter(page):
    _add_set(page)
    _add_set(page, headline="Bộ hai", desc="Mô tả hai", cta="Dùng thử")
    page.get_by_test_id("step-3").click()
    grid = page.get_by_test_id("preview-grid")
    pw.expect(grid.locator("figure")).to_have_count(12, timeout=20_000)   # 2 bộ × 6 kích thước
    pw.expect(grid.locator("figure .cv").first).to_be_visible(timeout=20_000)

    page.get_by_test_id("size-select").select_option("728x90")
    pw.expect(grid.locator("figure")).to_have_count(2, timeout=20_000)
    assert not page.errors, page.errors


def test_drag_and_resize_save_instantly(page):
    """Kéo thả và đổi cỡ chữ ngay trên ô, không bấm Áp dụng mà vẫn lưu."""
    _add_set(page)
    page.get_by_test_id("step-3").click()
    grid = page.get_by_test_id("preview-grid")
    pw.expect(grid.locator("figure")).to_have_count(6, timeout=20_000)

    card = grid.locator("figure").first
    box = card.locator("[data-testid$='-headline']").first
    pw.expect(box).to_be_visible(timeout=20_000)

    box.click()
    pw.expect(page.get_by_test_id("font-pct").first).to_have_text("100%")
    page.get_by_test_id("font-bigger").first.click()
    pw.expect(page.get_by_test_id("font-pct").first).to_have_text("110%")
    pw.expect(card.locator("figcaption")).to_contain_text("đã chỉnh")

    # kéo bằng bàn phím: lưu ngay, không có nút Áp dụng nào (đo sau khi đã đổi cỡ chữ)
    before = card.locator("[data-testid$='-headline']").first.bounding_box()
    box.focus()
    for _ in range(10):
        page.keyboard.press("ArrowDown")
    page.wait_for_timeout(300)
    after = card.locator("[data-testid$='-headline']").first.bounding_box()
    assert after["y"] > before["y"], (before, after)

    saved = page.evaluate("JSON.parse(localStorage.getItem('project'))")
    assert saved["positions"] and saved["scales"], saved
    assert not page.errors, page.errors


def test_cta_colour_changes_preview(page):
    _add_set(page)
    page.get_by_test_id("step-2").click()
    frame = page.frame_locator("[data-testid='live-preview']")
    pw.expect(frame.locator("#ad")).to_contain_text("Xem chi tiết")
    page.get_by_test_id("cta-color-d93025").click()
    page.wait_for_timeout(600)
    assert "#d93025" in frame.locator("#ad").inner_html()
    page.get_by_test_id("cta-color-auto").click()
    page.wait_for_timeout(600)
    assert "#d93025" not in frame.locator("#ad").inner_html()
    assert not page.errors, page.errors


def test_cta_style_switches(page):
    _add_set(page)
    page.get_by_test_id("step-2").click()
    frame = page.frame_locator("[data-testid='live-preview']")
    pw.expect(frame.locator("#ad")).to_contain_text("Xem chi tiết")
    # mặc định là chữ có màu: không có nền nút
    assert "border-radius" not in frame.locator("#ad").inner_html()
    page.get_by_test_id("cta-style-button").click()
    page.wait_for_timeout(600)
    assert "border-radius" in frame.locator("#ad").inner_html()
    assert not page.errors, page.errors


def test_resize_grips_change_width_and_font(page):
    """Kéo tay nắm cạnh phải đổi bề rộng ô chữ, kéo góc đổi cỡ chữ — lưu ngay."""
    _add_set(page, headline="Đọc PDF siêu nhanh", desc="Mở và sửa mọi tệp PDF trong vài giây")
    page.get_by_test_id("step-3").click()
    card = page.get_by_test_id("preview-grid").locator("figure").first
    box = card.locator("[data-testid$='-headline']").first
    pw.expect(box).to_be_visible(timeout=20_000)
    box.click()

    grip = card.get_by_test_id("grip-w-headline")
    pw.expect(grip).to_be_visible()
    before_w = box.bounding_box()["width"]
    g = grip.bounding_box()
    page.mouse.move(g["x"] + g["width"] / 2, g["y"] + g["height"] / 2)
    page.mouse.down()
    page.mouse.move(g["x"] - 70, g["y"] + g["height"] / 2, steps=6)
    page.mouse.up()
    page.wait_for_timeout(600)
    assert card.locator("[data-testid$='-headline']").first.bounding_box()["width"] < before_w - 10

    saved = page.evaluate("JSON.parse(localStorage.getItem('project'))")
    assert saved["widths"], saved

    pct_before = page.get_by_test_id("font-pct").first.inner_text()
    f = card.get_by_test_id("grip-f-headline").bounding_box()
    page.mouse.move(f["x"] + f["width"] / 2, f["y"] + f["height"] / 2)
    page.mouse.down()
    page.mouse.move(f["x"] + 40, f["y"] + 40, steps=6)
    page.mouse.up()
    page.wait_for_timeout(600)
    assert page.get_by_test_id("font-pct").first.inner_text() != pct_before
    assert not page.errors, page.errors


def test_drop_creatives_before_export(page, tmp_path):
    """Bỏ bớt creative không muốn lưu: số đếm giảm và file không được tạo ra."""
    _add_set(page)
    page.get_by_test_id("step-3").click()
    grid = page.get_by_test_id("preview-grid")
    pw.expect(grid.locator("figure")).to_have_count(6, timeout=20_000)
    pw.expect(page.get_by_test_id("kept")).to_contain_text("6/6")

    first = grid.locator("figure").first
    first.locator("input[type=checkbox]").uncheck()
    pw.expect(page.get_by_test_id("kept")).to_contain_text("5/6")

    page.get_by_test_id("step-4").click()
    pw.expect(page.get_by_test_id("run")).to_contain_text("(5)")
    out = tmp_path / "ra"
    out.mkdir()
    page.get_by_test_id("output-dir").fill(str(out))
    page.get_by_test_id("run").click()
    pw.expect(page.get_by_test_id("status")).to_contain_text("5/5", timeout=30_000)
    assert len(list(out.rglob("*.zip"))) == 5 + 1      # 5 creative + 1 file nén cả thư mục
    assert not page.errors, page.errors


def test_changing_language_translates_the_preset_cta(page):
    """Chọn nút mẫu tiếng Việt rồi đổi sang tiếng Hàn thì nút cũng sang tiếng Hàn."""
    page.get_by_test_id("headline").fill("Đọc PDF siêu nhanh")
    page.get_by_role("button", name="Xem chi tiết").click()
    pw.expect(page.get_by_test_id("cta")).to_have_value("Xem chi tiết")
    page.get_by_test_id("lang").select_option("ko")
    pw.expect(page.get_by_test_id("cta")).to_have_value("자세히 보기")
    # chữ tự gõ thì giữ nguyên, không bị đổi
    page.get_by_test_id("cta").fill("우리 문구")
    page.get_by_test_id("lang").select_option("en")
    pw.expect(page.get_by_test_id("cta")).to_have_value("우리 문구")
    assert not page.errors, page.errors


def test_output_format_is_visible_and_switchable(page, tmp_path):
    """Màn xuất file nói rõ sẽ tạo ra file HTML5, và đổi sang PNG được."""
    _add_set(page)
    page.get_by_test_id("step-4").click()
    pw.expect(page.get_by_test_id("opt-html")).to_be_checked()
    pw.expect(page.get_by_test_id("summary")).to_contain_text("HTML5")

    page.get_by_test_id("opt-html").uncheck()
    pw.expect(page.get_by_test_id("run")).to_be_disabled()
    page.get_by_test_id("opt-png").check()
    pw.expect(page.get_by_test_id("summary")).to_contain_text("PNG")

    out = tmp_path / "anh"
    out.mkdir()
    page.get_by_test_id("output-dir").fill(str(out))
    page.get_by_test_id("run").click()
    pw.expect(page.get_by_test_id("status")).to_contain_text("6/6", timeout=30_000)
    assert len(list(out.rglob("*.png"))) == 6 and not list(out.rglob("creatives_*/**/*.zip"))
    assert not page.errors, page.errors


def _reference_file(tmp_path):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1200, 630), (245, 245, 245))
    d = ImageDraw.Draw(img)
    d.rectangle([90, 80, 830, 160], fill=(20, 20, 20))       # tiêu đề trên-trái
    d.rectangle([92, 220, 700, 252], fill=(90, 90, 90))      # mô tả
    d.rectangle([980, 540, 1120, 580], fill=(232, 52, 26))   # CTA đỏ dưới-phải
    p = tmp_path / "mau.png"
    img.save(p)
    return str(p)


def test_reference_image_copies_layout(page, tmp_path):
    """Thả ảnh mẫu → tool đọc bố cục → áp cho mọi kích thước, không phải kéo tay."""
    _add_set(page)
    page.set_input_files("input[type=file]", _reference_file(tmp_path))
    pw.expect(page.get_by_test_id("ref-layout")).to_be_visible(timeout=15_000)
    pw.expect(page.get_by_test_id("ref-layout")).to_contain_text("Tiêu đề: trên · trái")
    pw.expect(page.get_by_test_id("ref-layout")).to_contain_text("Nút bấm: dưới · phải")

    page.get_by_test_id("apply-layout").click()
    page.get_by_test_id("step-3").click()
    card = page.get_by_test_id("preview-grid").locator("figure").first
    head = card.locator("[data-testid$='-headline']").first
    cta = card.locator("[data-testid$='-cta']").first
    pw.expect(head).to_be_visible(timeout=20_000)
    canvas = card.locator(".cv").first.bounding_box()
    hb, cb = head.bounding_box(), cta.bounding_box()
    # tiêu đề ở nửa trên bên trái, nút bấm ở nửa dưới bên phải — giống ảnh mẫu
    assert hb["y"] - canvas["y"] < canvas["height"] * 0.4
    assert cb["y"] - canvas["y"] > canvas["height"] * 0.55
    assert cb["x"] > hb["x"]
    assert not page.errors, page.errors


def test_ad_format_and_pulse_reach_the_export(page, tmp_path):
    """Chọn Toàn màn hình + nút nhấp nháy thì file xuất ra phải có đúng hai thứ đó."""
    import zipfile
    _add_set(page)
    page.get_by_test_id("step-2").click()
    page.get_by_test_id("ad-format-fullscreen").click()
    pw.expect(page.get_by_test_id("cta-pulse")).to_be_checked()

    page.get_by_test_id("step-4").click()
    out = tmp_path / "ra"
    out.mkdir()
    page.get_by_test_id("output-dir").fill(str(out))
    page.get_by_test_id("run").click()
    pw.expect(page.get_by_test_id("status")).to_contain_text("6/6", timeout=30_000)

    zips = sorted(out.rglob("*.zip"))
    with zipfile.ZipFile([z for z in zips if z.name.endswith(".zip") and "creatives_" not in z.name][0]) as z:
        html = z.read("index.html").decode()
    assert "exitapi.js" in html and "@keyframes adpulse" in html
    assert not page.errors, page.errors
