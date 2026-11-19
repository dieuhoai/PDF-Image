"""CLI: dùng khi muốn chạy tự động, không mở giao diện.

    html5adbuilder export noi-dung.csv ket-qua/ --sizes 300x250,728x90 --scheme clean_white
    html5adbuilder sizes
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, csv_import
from . import catalog as C
from .exporter import export
from .models import AdSize, Design, ExportOptions, ExportRequest, Project


def _sizes(text: str) -> list[AdSize]:
    if text.strip().lower() == "all":
        return [AdSize.parse(s["key"]) for s in C.SIZES]
    return [AdSize.parse(part) for part in text.split(",") if part.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="html5adbuilder", description="HTML5 Ad Builder — dòng lệnh")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sizes", help="Liệt kê kích thước có sẵn")
    sub.add_parser("schemes", help="Liệt kê bảng màu")
    e = sub.add_parser("export", help="Xuất creative từ file CSV")
    e.add_argument("csv", type=Path, help="File CSV nội dung (cột headline, description, cta, lang)")
    e.add_argument("output", type=Path, help="Thư mục chứa kết quả")
    e.add_argument("--sizes", default="300x250,728x90,320x50", help="Ví dụ 300x250,728x90 hoặc all")
    e.add_argument("--scheme", default="clean_white",
                   help=f"Một hoặc nhiều, cách nhau bởi dấu phẩy: {', '.join(C.SCHEMES)}")
    e.add_argument("--gradient", default="none")
    e.add_argument("--animation", default="fade")
    e.add_argument("--badge", default="", help=f"Cách nhau bởi dấu phẩy: {', '.join(C.BADGES)}")
    e.add_argument("--layout", default="auto")
    e.add_argument("--group-by", default="set", choices=C.GROUP_BY)
    e.add_argument("--click-url", default="https://www.google.com")
    e.add_argument("--png", action="store_true", help="Xuất thêm ảnh PNG tĩnh")
    e.add_argument("--no-zip", action="store_true", help="Không nén cả thư mục")
    e.add_argument("--json", action="store_true", help="In kết quả dạng JSON")
    a = ap.parse_args(argv)
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass

    if a.cmd == "sizes":
        print("\n".join(f"{s['key']:>10}  {s['group']}" for s in C.SIZES))
        return 0
    if a.cmd == "schemes":
        print("\n".join(f"{k:>12}  {v['name']}" for k, v in C.SCHEMES.items()))
        return 0

    try:
        sets, errors = csv_import.load(a.csv)
        for err in errors:
            print(f"  ! {err}", file=sys.stderr)
        if not sets:
            print("Lỗi: không đọc được bộ nội dung nào", file=sys.stderr)
            return 2
        project = Project(
            sets=sets,
            sizes=_sizes(a.sizes),
            design=Design(schemes=[s.strip() for s in a.scheme.split(",") if s.strip()], gradient=a.gradient,
                          animation=a.animation, layout=a.layout,
                          badges=[b.strip() for b in a.badge.split(",") if b.strip()]),
            export=ExportOptions(group_by=a.group_by, png=a.png, zip_all=not a.no_zip, click_url=a.click_url),
        )
        req = ExportRequest(project=project, output_dir=a.output)
    except (ValueError, OSError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 2

    def progress(done: int, total: int, item) -> None:
        if not a.json:
            print(f"[{done}/{total}] {'OK ' if item.ok else 'LỖI'} {item.name}")

    res = export(req, on_progress=progress)
    if a.json:
        print(json.dumps({"folder": str(res.folder), "zip": str(res.zip_path) if res.zip_path else None,
                          "ok": res.ok_count, "failed": [f.model_dump(mode="json") for f in res.failed]},
                         ensure_ascii=False, default=str))
    else:
        print(f"\nXong: {res.ok_count}/{len(res.items)} creative → {res.folder}")
        if res.zip_path:
            print(f"File nén: {res.zip_path}")
        for f in res.failed:
            print(f"  x {f.name}: {f.error}", file=sys.stderr)
        for w in sorted({w for i in res.items for w in i.warnings}):
            print(f"  ! {w}", file=sys.stderr)
    return 1 if res.failed else 0


if __name__ == "__main__":
    sys.exit(main())
