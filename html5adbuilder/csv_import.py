"""Nhập nhiều bộ nội dung từ file CSV do người dùng xuất ra từ Excel/Google Sheets.

Chấp nhận tên cột tiếng Việt lẫn tiếng Anh, dấu phân cách , ; hoặc tab, file có BOM.
Dòng lỗi không làm dừng cả file — trả về danh sách lỗi để UI hiển thị.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from pydantic import ValidationError

from .models import ContentSet

ALIASES: dict[str, str] = {
    "headline": "headline", "tieu de": "headline", "tiêu đề": "headline", "title": "headline",
    "description": "description", "mo ta": "description", "mô tả": "description", "desc": "description",
    "cta": "cta", "nut": "cta", "nút": "cta", "button": "cta",
    "lang": "lang", "language": "lang", "ngon ngu": "lang", "ngôn ngữ": "lang",
    "name": "name", "ten": "name", "tên": "name", "ten bo": "name", "tên bộ": "name", "set": "name",
}


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "utf-16", "cp1258", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _dialect(sample: str) -> type[csv.Dialect] | csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def parse(text: str) -> tuple[list[ContentSet], list[str]]:
    text = text.lstrip("﻿")
    reader = csv.DictReader(io.StringIO(text), dialect=_dialect(text[:2000]))
    if not reader.fieldnames:
        return [], ["File rỗng — cần dòng tiêu đề có cột headline, cta, lang"]
    colmap = {h: ALIASES.get((h or "").strip().lower(), "") for h in reader.fieldnames}
    found = set(colmap.values())
    missing = [c for c in ("headline", "cta") if c not in found]
    if missing:
        have = ", ".join(h for h in reader.fieldnames if h)
        return [], [f"Thiếu cột bắt buộc: {', '.join(missing)}. File đang có: {have}"]

    sets: list[ContentSet] = []
    errors: list[str] = []
    for i, row in enumerate(reader, start=2):  # dòng 1 là tiêu đề
        data = {colmap[h]: (v or "").strip() for h, v in row.items() if h and colmap.get(h)}
        if not any(data.values()):
            continue
        data.setdefault("lang", "en")
        if not data.get("lang"):
            data["lang"] = "en"
        try:
            sets.append(ContentSet(**data))
        except ValidationError as e:
            why = "; ".join(err["msg"].replace("Value error, ", "") for err in e.errors())
            errors.append(f"Dòng {i}: {why}")
    if not sets and not errors:
        errors.append("Không có dòng dữ liệu nào trong file")
    return sets, errors


def load(path: Path) -> tuple[list[ContentSet], list[str]]:
    raw = Path(path).read_bytes()
    return parse(_decode(raw))
