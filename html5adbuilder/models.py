"""Model dữ liệu (pydantic). Mọi input từ CLI/Web đều đi qua đây để được validate."""
from __future__ import annotations

import re
import uuid
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from . import catalog as C


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


class ContentSet(BaseModel):
    """Một bộ nội dung: headline + description + CTA + ngôn ngữ."""

    id: str = Field(default_factory=_new_id, pattern=r"^[A-Za-z0-9_-]{1,32}$")
    name: str = Field(default="", max_length=60)
    headline: str
    description: str = ""
    cta: str
    lang: str = "en"

    @field_validator("headline", "description", "cta", "name", mode="before")
    @classmethod
    def _strip(cls, v: object) -> object:
        return v.strip() if isinstance(v, str) else v

    @field_validator("headline")
    @classmethod
    def _headline(cls, v: str) -> str:
        if not v:
            raise ValueError("Headline không được để trống")
        if len(v) > 20:
            raise ValueError(f"Headline tối đa 20 ký tự (đang có {len(v)})")
        return v

    @field_validator("description")
    @classmethod
    def _desc(cls, v: str) -> str:
        if len(v) > 100:
            raise ValueError(f"Description tối đa 100 ký tự (đang có {len(v)})")
        return v

    @field_validator("cta")
    @classmethod
    def _cta(cls, v: str) -> str:
        if not v:
            raise ValueError("CTA không được để trống")
        if len(v) > 25:
            raise ValueError(f"CTA tối đa 25 ký tự (đang có {len(v)})")
        return v

    @field_validator("lang")
    @classmethod
    def _lang(cls, v: str) -> str:
        v = (v or "").strip().lower()
        if v not in C.LANGUAGES:
            raise ValueError(f"Ngôn ngữ {v!r} chưa hỗ trợ. Dùng một trong: {', '.join(C.LANGUAGES)}")
        return v

    @property
    def label(self) -> str:
        return self.name or self.headline


_SIZE_RE = re.compile(r"^\s*(\d{2,4})\s*[x×X*]\s*(\d{2,4})\s*$")


class AdSize(BaseModel, frozen=True):
    w: int = Field(ge=10, le=2000)
    h: int = Field(ge=10, le=2000)

    @classmethod
    def parse(cls, text: str) -> AdSize:
        m = _SIZE_RE.match(text or "")
        if not m:
            raise ValueError(f"Kích thước {text!r} không đúng dạng RỘNGxCAO, ví dụ 300x250")
        return cls(w=int(m.group(1)), h=int(m.group(2)))

    @property
    def key(self) -> str:
        return f"{self.w}x{self.h}"


class Design(BaseModel):
    schemes: list[str] = Field(default_factory=lambda: ["clean_white"])
    gradient: str = "none"
    animation: str = "fade"
    badges: list[str] = Field(default_factory=list)
    layout: str = "auto"
    cta_style: str = "text"
    cta_color: str = ""          # rỗng = dùng màu nhấn của bảng màu
    cta_pulse: bool = True       # nút đập nhẹ liên tục cho bắt mắt
    ad_format: str = "banner"    # "fullscreen" = tự co vừa màn hình + dùng ExitApi

    @field_validator("schemes")
    @classmethod
    def _schemes(cls, v: list[str]) -> list[str]:
        v = list(dict.fromkeys(v))
        if not v:
            raise ValueError("Chọn ít nhất 1 bảng màu")
        bad = [s for s in v if s not in C.SCHEMES]
        if bad:
            raise ValueError(f"Bảng màu không có: {bad}")
        return v

    @field_validator("badges")
    @classmethod
    def _badges(cls, v: list[str]) -> list[str]:
        v = list(dict.fromkeys(v))
        bad = [b for b in v if b not in C.BADGES]
        if bad:
            raise ValueError(f"Badge không có: {bad}")
        return v

    @model_validator(mode="after")
    def _enums(self) -> Design:
        if self.gradient != "none" and self.gradient not in C.GRADIENTS:
            raise ValueError(f"Gradient không có: {self.gradient}")
        if self.animation not in C.ANIMATIONS:
            raise ValueError(f"Animation không có: {self.animation}")
        if self.layout not in C.LAYOUTS:
            raise ValueError(f"Bố cục không có: {self.layout}")
        if self.cta_style not in C.CTA_STYLES:
            raise ValueError(f"Kiểu nút bấm không có: {self.cta_style}")
        if self.ad_format not in C.AD_FORMATS:
            raise ValueError(f"Kiểu quảng cáo không có: {self.ad_format}")
        if self.cta_color and not re.match(r"^#[0-9a-fA-F]{6}$", self.cta_color):
            raise ValueError(f"Màu nút bấm phải dạng #rrggbb, ví dụ #1a73e8 (đang là {self.cta_color!r})")
        return self


class Pos(BaseModel):
    """Vị trí góc trên-trái của một thành phần, tính theo tỉ lệ khung (0–1)."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class ExportOptions(BaseModel):
    html: bool = True            # file HTML5 .zip để upload Google Ads — đầu ra chính
    group_by: str = "set"
    manifest: bool = True
    preview: bool = True
    png: bool = False
    png_scale: int = Field(default=2, ge=1, le=4)   # 2 = ảnh nét gấp đôi
    zip_all: bool = True
    click_url: str = "https://www.google.com"

    @field_validator("group_by")
    @classmethod
    def _group(cls, v: str) -> str:
        if v not in C.GROUP_BY:
            raise ValueError(f"Cách gom file không có: {v}")
        return v

    @model_validator(mode="after")
    def _one_format(self) -> ExportOptions:
        if not self.html and not self.png:
            raise ValueError("Chọn ít nhất một định dạng: file HTML5 hoặc ảnh PNG")
        return self

    @field_validator("click_url")
    @classmethod
    def _url(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^https?://[^\s\"'<>\\]+$", v):
            raise ValueError("Link đích phải bắt đầu bằng http:// hoặc https:// và không có khoảng trắng")
        return v


# key của positions/scales: "300x250" (cả size) hoặc "<set_id>/300x250" (một bộ ở size đó).
Positions = dict[str, dict[str, Pos]]
# Hệ số cỡ chữ từng thành phần: 1.0 = cỡ tool tự tính.
Scales = dict[str, dict[str, float]]
MIN_SCALE, MAX_SCALE = 0.4, 3.0
# Bề rộng ô chứa chữ, tính theo phần của bề rộng dùng được: 1.0 = full, 0.5 = một nửa.
Widths = dict[str, dict[str, float]]
MIN_WIDTH, MAX_WIDTH = 0.15, 1.0
# Chỉ hai khối này mới xuống dòng, nên mới chỉnh được bề rộng.
WIDTH_ELEMENTS = ("headline", "description")


class Creative(BaseModel):
    content: ContentSet
    size: AdSize
    scheme: str
    badge: str | None = None

    @property
    def key(self) -> str:
        """Khoá nhận dạng một creative — dùng để bỏ bớt những cái không muốn xuất."""
        return f"{self.content.id}|{self.size.key}|{self.scheme}|{self.badge or '-'}"


class Project(BaseModel):
    sets: list[ContentSet] = Field(default_factory=list)
    sizes: list[AdSize] = Field(default_factory=lambda: [AdSize(w=300, h=250)])
    design: Design = Field(default_factory=Design)
    positions: Positions = Field(default_factory=dict)
    scales: Scales = Field(default_factory=dict)
    widths: Widths = Field(default_factory=dict)
    excluded: list[str] = Field(default_factory=list)   # khoá các creative người dùng không muốn xuất
    export: ExportOptions = Field(default_factory=ExportOptions)

    @field_validator("sizes")
    @classmethod
    def _dedupe(cls, v: list[AdSize]) -> list[AdSize]:
        return list(dict.fromkeys(v))

    @field_validator("positions")
    @classmethod
    def _pos_keys(cls, v: Positions) -> Positions:
        for key, elems in v.items():
            AdSize.parse(key.split("/", 1)[-1])
            bad = [e for e in elems if e not in C.ELEMENTS]
            if bad:
                raise ValueError(f"Thành phần không có: {bad}")
        return v

    @field_validator("scales")
    @classmethod
    def _scale_keys(cls, v: Scales) -> Scales:
        for key, elems in v.items():
            AdSize.parse(key.split("/", 1)[-1])
            for element, value in elems.items():
                if element not in C.ELEMENTS:
                    raise ValueError(f"Thành phần không có: {element}")
                if not MIN_SCALE <= value <= MAX_SCALE:
                    raise ValueError(f"Cỡ chữ phải trong khoảng {MIN_SCALE}–{MAX_SCALE} lần")
        return v

    @field_validator("widths")
    @classmethod
    def _width_keys(cls, v: Widths) -> Widths:
        for key, elems in v.items():
            AdSize.parse(key.split("/", 1)[-1])
            for element, value in elems.items():
                if element not in WIDTH_ELEMENTS:
                    raise ValueError(f"Chỉ chỉnh được bề rộng của: {', '.join(WIDTH_ELEMENTS)}")
                if not MIN_WIDTH <= value <= MAX_WIDTH:
                    raise ValueError(f"Bề rộng phải trong khoảng {MIN_WIDTH}–{MAX_WIDTH}")
        return v

    @property
    def creative_count(self) -> int:
        """Số creative thật sự sẽ xuất (đã trừ những cái bị bỏ)."""
        return sum(1 for _ in self.creatives())

    def all_creatives(self) -> Iterator[Creative]:
        """Mọi tổ hợp, kể cả những cái đã bỏ — dùng để hiện lưới xem trước."""
        badges: list[str | None] = list(self.design.badges) or [None]
        for s in self.sets:
            for size in self.sizes:
                for scheme in self.design.schemes:
                    for b in badges:
                        yield Creative(content=s, size=size, scheme=scheme, badge=b)

    def creatives(self) -> Iterator[Creative]:
        skip = set(self.excluded)
        for cr in self.all_creatives():
            if cr.key not in skip:
                yield cr

    def positions_for(self, set_id: str, size: AdSize) -> dict[str, Pos]:
        """Ghi đè theo bộ thắng ghi đè theo size (theo từng thành phần)."""
        return {**self.positions.get(size.key, {}), **self.positions.get(f"{set_id}/{size.key}", {})}

    def scales_for(self, set_id: str, size: AdSize) -> dict[str, float]:
        """Hệ số cỡ chữ áp cho một bộ ở một kích thước, theo cùng thứ tự ưu tiên như vị trí."""
        return {**self.scales.get(size.key, {}), **self.scales.get(f"{set_id}/{size.key}", {})}

    def widths_for(self, set_id: str, size: AdSize) -> dict[str, float]:
        """Bề rộng ô chữ áp cho một bộ ở một kích thước."""
        return {**self.widths.get(size.key, {}), **self.widths.get(f"{set_id}/{size.key}", {})}


class ExportRequest(BaseModel):
    project: Project
    output_dir: Path

    @model_validator(mode="after")
    def _has_work(self) -> ExportRequest:
        if not self.project.sets:
            raise ValueError("Chưa có bộ nội dung nào")
        if not self.project.sizes:
            raise ValueError("Chưa chọn kích thước nào")
        if not self.project.creative_count:
            raise ValueError("Đã bỏ hết creative — hãy giữ lại ít nhất một cái để xuất")
        return self


class ItemResult(BaseModel):
    name: str
    output: Path | None = None
    ok: bool
    error: str | None = None
    bytes: int = 0
    warnings: list[str] = Field(default_factory=list)


class JobResult(BaseModel):
    items: list[ItemResult]
    folder: Path | None = None
    zip_path: Path | None = None

    @property
    def ok_count(self) -> int:
        return sum(1 for i in self.items if i.ok)

    @property
    def failed(self) -> list[ItemResult]:
        return [i for i in self.items if not i.ok]
