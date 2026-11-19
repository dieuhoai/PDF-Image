"""Thư viện: lưu/mở lại bộ nội dung + cấu hình đã dùng, và mở thư mục kết quả."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from html5adbuilder import defaults as D
from html5adbuilder.io_utils import read_json, write_json
from html5adbuilder.models import Project

router = APIRouter(prefix="/api/library")
_SAFE = re.compile(r"^[^\\/:*?\"<>|]{1,60}$")


def _dir() -> Path:
    p = D.USER_DIR / "projects"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _path(name: str) -> Path:
    if not _SAFE.match(name or ""):
        raise HTTPException(422, "Tên không hợp lệ (không dùng \\ / : * ? \" < > |)")
    return _dir() / f"{name}.json"


@router.get("")
def list_saved() -> dict:
    items = []
    for p in sorted(_dir().glob("*.json")):
        data = read_json(p, {}) or {}
        items.append({"name": p.stem, "sets": len(data.get("sets", [])),
                      "saved": round(p.stat().st_mtime)})
    return {"items": items}


class SaveBody(BaseModel):
    name: str
    project: Project


@router.put("")
def save(body: SaveBody) -> dict:
    write_json(_path(body.name), body.project.model_dump(mode="json"))
    return {"saved": body.name}


@router.get("/{name}")
def load(name: str) -> dict:
    p = _path(name)
    if not p.is_file():
        raise HTTPException(404, f"Không có bản lưu tên {name!r}")
    try:
        return {"project": Project.model_validate(read_json(p, {})).model_dump(mode="json")}
    except ValidationError as e:
        raise HTTPException(422, f"Bản lưu hỏng: {e.errors()[0]['msg']}") from e


@router.delete("/{name}")
def delete(name: str) -> dict:
    _path(name).unlink(missing_ok=True)
    return {"deleted": name}


class OpenBody(BaseModel):
    path: str


@router.post("/reveal")
def reveal(body: OpenBody) -> dict:
    """Mở thư mục kết quả trong Finder/Explorer."""
    p = Path(body.path)
    if not p.exists():
        raise HTTPException(404, "Không thấy thư mục này nữa")
    target = p if p.is_dir() else p.parent
    cmd = {"darwin": ["open", str(target)], "win32": ["explorer", str(target)]}.get(sys.platform,
                                                                                   ["xdg-open", str(target)])
    try:
        subprocess.Popen(cmd)  # noqa: S603 — lệnh cố định của hệ điều hành, đường dẫn truyền dạng list
    except OSError as e:
        raise HTTPException(500, f"Không mở được thư mục: {e}") from e
    return {"opened": str(target)}
