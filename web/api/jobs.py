"""Chạy việc xuất trong thread nền, đẩy tiến độ qua WebSocket. Chỉ 1 việc tại một thời điểm."""
from __future__ import annotations

import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from html5adbuilder.exporter import export
from html5adbuilder.models import ExportRequest, Project

from ..state import STATE

router = APIRouter(prefix="/api/jobs")
_lock = threading.Lock()


def _worker(req: ExportRequest) -> None:
    try:
        res = export(
            req,
            on_progress=lambda d, t, it: STATE.update_job(done=d, total=t, last=it.model_dump(mode="json")),
            should_stop=STATE.stop_flag.is_set,
        )
        STATE.update_job(
            status="stopped" if STATE.stop_flag.is_set() else "done",
            ok=res.ok_count,
            folder=str(res.folder) if res.folder else None,
            zip_path=str(res.zip_path) if res.zip_path else None,
            warnings=sorted({w for i in res.items for w in i.warnings}),
            failed=[f.model_dump(mode="json") for f in res.failed],
        )
    except Exception as e:  # noqa: BLE001 — báo lỗi lên UI thay vì chết im lặng
        STATE.update_job(status="error", error=str(e))
    finally:
        _lock.release()


@router.post("")
def start(body: dict) -> dict:
    try:
        project = Project.model_validate(body.get("project", {}))
        req = ExportRequest(project=project, output_dir=Path(body.get("output_dir", "")))
    except ValidationError as e:
        raise HTTPException(422, "; ".join(err["msg"].replace("Value error, ", "") for err in e.errors())) from e
    if not req.output_dir.is_dir():
        raise HTTPException(422, "Thư mục kết quả không tồn tại — hãy bấm Chọn… để chọn lại")
    if not _lock.acquire(blocking=False):
        raise HTTPException(409, "Đang xuất, chờ xong rồi chạy tiếp")
    STATE.stop_flag.clear()
    STATE.update_job(status="running", done=0, total=project.creative_count, ok=0, failed=[], error=None,
                     last=None, folder=None, zip_path=None, warnings=[])
    threading.Thread(target=_worker, args=(req,), daemon=True).start()
    return {"started": True, "total": project.creative_count}


@router.post("/stop")
def stop() -> dict:
    STATE.stop_flag.set()
    return {"stopping": True}


@router.get("")
def status() -> dict:
    return STATE.snapshot()["job"]
