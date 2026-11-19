"""API tra cứu danh mục + kiểm CTA + nhập CSV + gợi ý màu + xem trước."""
from __future__ import annotations

import base64
import binascii
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from html5adbuilder import analyze as A
from html5adbuilder import catalog as C
from html5adbuilder import csv_import, cta, palette, recipe, render_html
from html5adbuilder.models import (
    MAX_SCALE,
    MAX_WIDTH,
    MIN_SCALE,
    MIN_WIDTH,
    WIDTH_ELEMENTS,
    AdSize,
    ContentSet,
    Creative,
    Design,
    Pos,
)

router = APIRouter(prefix="/api")


@router.get("/catalog")
def get_catalog() -> dict:
    return {
        "sizes": C.SIZES,
        "schemes": [{"key": k, **v} for k, v in C.SCHEMES.items()],
        "gradients": [{"key": k, **v} for k, v in C.GRADIENTS.items()],
        "badges": [{"key": k, **v} for k, v in C.BADGES.items()],
        "languages": [{"key": k, "name": v} for k, v in C.LANGUAGES.items()],
        "cta_presets": C.CTA_PRESETS,
        "animations": C.ANIMATIONS,
        "layouts": C.LAYOUTS,
        "cta_styles": C.CTA_STYLES,
        "ad_formats": C.AD_FORMATS,
        "cta_colors": C.CTA_COLORS,
        "png_scales": [1, 2, 3, 4],
        "group_by": C.GROUP_BY,
        "elements": C.ELEMENTS,
        "max_zip_kb": C.MAX_ZIP_BYTES // 1024,
        "scale_range": [MIN_SCALE, MAX_SCALE],
        "width_range": [MIN_WIDTH, MAX_WIDTH],
        "width_elements": list(WIDTH_ELEMENTS),
    }


@router.get("/banned-cta")
def get_banned() -> dict:
    return {"words": cta.load_banned()}


class BannedBody(BaseModel):
    words: list[str] = []


@router.put("/banned-cta")
def put_banned(body: BannedBody) -> dict:
    return {"words": cta.save_banned(body.words)}


@router.post("/banned-cta/reset")
def reset_banned() -> dict:
    return {"words": cta.reset_banned()}


class CtaBody(BaseModel):
    text: str = ""


@router.post("/cta/check")
def check_cta(body: CtaBody) -> dict:
    words = cta.load_banned()
    found = cta.find_banned(body.text, words)
    return {"ok": not found and bool(body.text.strip()), "banned": found}


class CsvBody(BaseModel):
    text: str | None = None
    path: str | None = None


@router.post("/csv/import")
def import_csv(body: CsvBody) -> dict:
    if body.path:
        p = Path(body.path)
        if not p.is_file():
            raise HTTPException(422, f"Không thấy file {p.name}")
        try:
            sets, errors = csv_import.load(p)
        except OSError as e:
            raise HTTPException(422, f"Không đọc được file: {e}") from e
    elif body.text is not None:
        sets, errors = csv_import.parse(body.text)
    else:
        raise HTTPException(422, "Cần gửi nội dung CSV hoặc đường dẫn file")
    return {"sets": [s.model_dump(mode="json") for s in sets], "errors": errors}


class ImageBody(BaseModel):
    data_url: str | None = None
    path: str | None = None


@router.post("/palette/suggest")
def suggest_palette(body: ImageBody) -> dict:
    try:
        if body.data_url:
            raw = body.data_url.split(",", 1)[-1]
            return palette.suggest_bytes(base64.b64decode(raw, validate=True))
        if body.path:
            return palette.suggest(Path(body.path))
    except (ValueError, binascii.Error) as e:
        raise HTTPException(422, str(e)) from e
    raise HTTPException(422, "Cần gửi ảnh")


class ReferenceBody(BaseModel):
    data_url: str | None = None
    path: str | None = None
    sizes: list[str] = []
    design: Design = Design()
    sets: list[ContentSet] = []


@router.post("/reference")
def reference(body: ReferenceBody) -> dict:
    """Đọc ảnh mẫu: trả về màu gợi ý + bố cục (chỗ đặt, cỡ chữ) áp sẵn cho từng kích thước."""
    try:
        if body.data_url:
            raw = base64.b64decode(body.data_url.split(",", 1)[-1], validate=True)
            analysis = A.analyze_bytes(raw)
            colors = palette.suggest_bytes(raw)
        elif body.path:
            analysis = A.analyze(Path(body.path))
            colors = palette.suggest(Path(body.path))
        else:
            raise HTTPException(422, "Cần gửi ảnh")
        sizes = [AdSize.parse(k) for k in body.sizes] or [AdSize(w=300, h=250)]
    except (ValueError, binascii.Error) as e:
        raise HTTPException(422, str(e)) from e
    plan = recipe.from_analysis(analysis, sizes, body.design, body.sets)
    return {
        **colors,
        "layout_found": bool(analysis.get("roles")),
        "blocks": recipe.describe(analysis),
        "plan": {
            "positions": {k: {e: p.model_dump() for e, p in v.items()} for k, v in plan["positions"].items()},
            "scales": plan["scales"],
            "widths": plan["widths"],
            "cta_color": plan["cta_color"],
            "layout": plan["layout"],
        },
    }


class PreviewBody(BaseModel):
    content: ContentSet
    size: str = "300x250"
    scheme: str = "clean_white"
    badge: str | None = None
    design: Design = Design()
    positions: dict[str, Pos] = {}
    scales: dict[str, float] = {}
    widths: dict[str, float] = {}
    click_url: str = "https://www.google.com"
    animate: bool = True


@router.post("/preview")
def preview(body: PreviewBody) -> dict:
    """Trả về HTML của một creative để UI nhúng vào iframe xem trước."""
    try:
        size = AdSize.parse(body.size)
        cr = Creative(content=body.content, size=size, scheme=body.scheme, badge=body.badge)
        html = render_html.render(cr, body.design, body.click_url, body.positions or None,
                                  body.animate, body.scales or None, body.widths or None)
    except (ValueError, ValidationError) as e:
        raise HTTPException(422, str(e)) from e
    from html5adbuilder import layout as L
    lay = L.build(cr, body.design, body.positions or None, body.scales or None, body.widths or None)
    return {
        "html": html,
        "colors": render_html.colors(body.scheme, body.design.gradient, body.design.cta_color),
        "cta_style": body.design.cta_style,
        "bytes": len(html.encode()),
        "warnings": lay.warnings,
        "boxes": [b.model_dump(mode="json") for b in lay.boxes],
        "size": {"w": size.w, "h": size.h},
    }
