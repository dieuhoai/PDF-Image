"""Xuất hàng loạt: từng creative thành một ZIP HTML5, kèm manifest, trang preview và báo cáo.

Nguyên tắc: lỗi một creative không làm dừng cả lô; mọi tên file đều ASCII an toàn và không trùng;
có thể dừng giữa chừng (`should_stop`) và báo tiến độ (`on_progress`).
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import re
import unicodedata
import zipfile
from collections.abc import Callable
from pathlib import Path

from . import __version__, fonts, render_html, render_png
from . import catalog as C
from .io_utils import atomic_write_text, write_json
from .models import Creative, ExportRequest, ItemResult, JobResult

Progress = Callable[[int, int, ItemResult], None]

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def slug(text: str, fallback: str = "set") -> str:
    """Tên file an toàn trên cả Windows/macOS: bỏ dấu, bỏ emoji, chỉ còn chữ-số-gạch."""
    norm = unicodedata.normalize("NFKD", text or "")
    ascii_only = "".join(c for c in norm if not unicodedata.combining(c))
    ascii_only = ascii_only.replace("đ", "d").replace("Đ", "D")
    out = _UNSAFE.sub("-", ascii_only).strip("-._")
    out = re.sub(r"-{2,}", "-", out)[:48]
    return out or fallback


def unique_dir(parent: Path, name: str) -> Path:
    """creatives_2026-11-18, nếu đã có thì -2, -3…"""
    cand = parent / name
    i = 2
    while cand.exists():
        cand = parent / f"{name}-{i}"
        i += 1
    return cand


HTML_DIR = "html5"      # file .zip để upload Google Ads
IMAGE_DIR = "images"    # ảnh PNG tĩnh


def _rel_path(cr: Creative, group_by: str, set_slug: str, suffix: str, multi: dict[str, bool]) -> Path:
    """Đường dẫn tương đối của một creative trong thư mục kết quả."""
    extra = ""
    if multi["scheme"]:
        extra += f"_{cr.scheme}"
    if multi["badge"] and cr.badge:
        extra += f"_{cr.badge}"
    size = cr.size.key
    if group_by == "set":
        return Path(set_slug) / f"{size}{extra}{suffix}"
    if group_by == "size":
        return Path(size) / f"{set_slug}{extra}{suffix}"
    return Path(f"{set_slug}_{size}{extra}{suffix}")


def _set_slugs(req: ExportRequest) -> dict[str, str]:
    """Mỗi bộ một tên file riêng, không trùng nhau kể cả khi tên gốc khác dấu."""
    used: set[str] = set()
    out: dict[str, str] = {}
    for i, s in enumerate(req.project.sets, 1):
        base = slug(s.label, f"set{i}")
        name, n = base, 2
        while name.lower() in used:
            name, n = f"{base}-{n}", n + 1
        used.add(name.lower())
        out[s.id] = name
    return out


def export(req: ExportRequest, on_progress: Progress | None = None,
           should_stop: Callable[[], bool] | None = None) -> JobResult:
    project = req.project
    opt = project.export
    slugs = _set_slugs(req)
    creatives = list(project.creatives())
    total = len(creatives)
    multi = {"scheme": len(project.design.schemes) > 1, "badge": len(project.design.badges) > 1}

    folder = unique_dir(Path(req.output_dir), f"creatives_{dt.date.today():%Y-%m-%d}")
    folder.mkdir(parents=True, exist_ok=True)

    items: list[ItemResult] = []
    manifest: list[dict] = []
    for i, cr in enumerate(creatives, 1):
        if should_stop and should_stop():
            break
        rel = _rel_path(cr, opt.group_by, slugs[cr.content.id], ".zip" if opt.html else ".png", multi)
        if opt.html and opt.png:
            rel = Path(HTML_DIR) / rel          # xuất cả hai thì tách hẳn hai thư mục
        item = _one(cr, project, folder, rel, opt, manifest)
        items.append(item)
        if on_progress:
            on_progress(i, total, item)

    if opt.manifest:
        write_json(folder / "manifest.json", {
            "generator": f"HTML5 Ad Builder {__version__}",
            "created": dt.datetime.now().isoformat(timespec="seconds"),
            "count": len(manifest),
            "click_url": opt.click_url,
            "creatives": manifest,
        })
    if opt.preview:
        atomic_write_text(folder / "preview" / "index.html", _preview_page(manifest, folder))
    _write_report(folder / "report.csv", items)

    zip_path = _zip_folder(folder) if opt.zip_all else None
    return JobResult(items=items, folder=folder, zip_path=zip_path)


def _one(cr: Creative, project, folder: Path, rel: Path, opt, manifest: list[dict]) -> ItemResult:
    name = rel.as_posix()
    try:
        positions = project.positions_for(cr.content.id, cr.size)
        scales = project.scales_for(cr.content.id, cr.size)
        widths = project.widths_for(cr.content.id, cr.size)
        from . import layout as L
        warnings = L.build(cr, project.design, positions, scales, widths).warnings
        out = folder / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "file": name, "set": cr.content.label, "size": cr.size.key, "scheme": cr.scheme,
            "badge": cr.badge, "lang": cr.content.lang,
            "headline": cr.content.headline, "description": cr.content.description, "cta": cr.content.cta,
            "warnings": warnings,
        }
        main, written = out, 0
        if opt.html:
            data = render_html.zip_bytes(cr, project.design, opt.click_url, positions, scales, widths)
            out.write_bytes(data)
            written = len(data)
        if opt.png:
            if cr.content.lang in C.COMPLEX_SCRIPT_LANGS and not fonts.shapes_complex_text():
                warnings = [*warnings,
                            f"{cr.size.key}: ảnh PNG tiếng {C.LANGUAGES[cr.content.lang]} có thể đặt sai dấu "
                            "— bản HTML5 vẫn đúng, nên dùng bản HTML5 để chạy quảng cáo"]
            png = out.with_suffix(".png")
            if opt.html:
                # đổi html5/... thành images/... để ảnh nằm riêng một thư mục
                png = folder / IMAGE_DIR / png.relative_to(folder / HTML_DIR)
                png.parent.mkdir(parents=True, exist_ok=True)
            png.write_bytes(render_png.png_bytes(cr, project.design, positions, scales, widths, opt.png_scale))
            entry["png"] = png.relative_to(folder).as_posix()
            if not opt.html:
                main, written, name = png, png.stat().st_size, entry["png"]
                entry["file"] = name
        entry["bytes"] = written
        entry["html"] = opt.html
        manifest.append(entry)
        entry["warnings"] = warnings
        return ItemResult(name=name, output=main, ok=True, bytes=written, warnings=warnings)
    except Exception as e:  # noqa: BLE001 — lỗi 1 creative không được làm hỏng cả lô
        return ItemResult(name=name, ok=False, error=f"{e}")


def _preview_page(manifest: list[dict], folder: Path) -> str:
    """Trang xem tất cả creative dạng lưới — mở bằng trình duyệt, không cần mạng."""
    from html import escape
    cards = []
    for m in manifest:
        w, h = m["size"].split("x")
        if m.get("html"):
            src = f"../{m['file'][:-4]}_preview.html"   # bản HTML giải nén để xem (ghi bên dưới)
            view = (f'<iframe src="{escape(src)}" width="{w}" height="{h}" loading="lazy" '
                    f'title="{escape(m["set"])} {m["size"]}" sandbox="allow-scripts"></iframe>')
        else:
            view = (f'<img src="../{escape(m["png"])}" width="{w}" height="{h}" loading="lazy" '
                    f'alt="{escape(m["set"])} {m["size"]}">')
        cards.append(
            f'<figure>{view}'
            f'<figcaption>{escape(m["set"])} · {m["size"]}'
            f'{" · " + escape(m["scheme"]) if m.get("scheme") else ""} · {m["bytes"] // 1024 or 1} KB'
            f'</figcaption></figure>')
    # Giải nén sẵn bản xem thử cạnh file zip để iframe hiển thị được.
    for m in manifest:
        if not m.get("html"):
            continue
        zp = folder / m["file"]
        try:
            with zipfile.ZipFile(zp) as z:
                (zp.parent / f"{zp.stem}_preview.html").write_bytes(z.read("index.html"))
        except (OSError, KeyError, zipfile.BadZipFile):
            pass
    return (
        "<!doctype html>\n<html lang=\"vi\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Xem tất cả creative</title><style>"
        "body{font:14px/1.5 system-ui,sans-serif;background:#f6f6fa;color:#15151f;margin:0;padding:24px}"
        "h1{font-size:18px} .grid{display:flex;flex-wrap:wrap;gap:20px;align-items:flex-start}"
        "figure{margin:0;background:#fff;border:1px solid #dcdce6;border-radius:10px;padding:10px}"
        "iframe,img{border:0;display:block;max-width:100%}"
        "figcaption{margin-top:8px;color:#5a5a6e;font-size:12px}"
        "@media(prefers-color-scheme:dark){body{background:#0b0b14;color:#e7e7f5}"
        "figure{background:#20202e;border-color:#33334a}figcaption{color:#a9a9be}}"
        "</style></head><body>"
        f"<h1>{len(manifest)} creative</h1><div class=\"grid\">{''.join(cards)}</div></body></html>\n"
    )


def _write_report(path: Path, items: list[ItemResult]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["file", "ket_qua", "dung_luong_byte", "canh_bao", "loi"])
    for it in items:
        w.writerow([it.name, "OK" if it.ok else "LỖI", it.bytes, " | ".join(it.warnings), it.error or ""])
    atomic_write_text(path, buf.getvalue())


def _zip_folder(folder: Path) -> Path:
    """Nén cả thư mục kết quả thành một file để gửi đi."""
    zip_path = folder.with_suffix(".zip")
    i = 2
    while zip_path.exists():
        zip_path = folder.parent / f"{folder.name}-{i}.zip"
        i += 1
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(folder.parent).as_posix())
    return zip_path


MAX_ZIP_BYTES = C.MAX_ZIP_BYTES
