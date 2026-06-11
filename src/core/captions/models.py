"""Serializable caption style and text-overlay models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

OverlayKind = Literal["title", "watermark", "cta", "custom"]


class CaptionStyleModel(BaseModel):
    """ASS caption style parameters. Colors use RGB tuples."""

    name: str = "bold_outline"
    font: str = "Arial Black"
    font_size: int = 64
    primary_rgb: tuple[int, int, int] = (255, 255, 255)
    highlight_rgb: tuple[int, int, int] = (255, 214, 10)
    outline_rgb: tuple[int, int, int] = (0, 0, 0)
    back_rgb: tuple[int, int, int] = (0, 0, 0)
    outline_px: int = 6
    shadow_px: int = 0
    bold: bool = True
    italic: bool = False
    uppercase: bool = True
    max_chars_per_line: int = 22
    max_words_per_line: int = 6
    bottom_margin_px: int = 220
    border_style: int = 1
    builtin: bool = False

    # Remotion-style extensions
    primary_opacity: int = Field(default=100, ge=0, le=100)
    highlight_opacity: int = Field(default=100, ge=0, le=100)
    outline_opacity: int = Field(default=100, ge=0, le=100)
    back_opacity: int = Field(default=0, ge=0, le=100)
    fade_in_ms: int = Field(default=0, ge=0)
    fade_out_ms: int = Field(default=0, ge=0)
    alignment: int = Field(default=2, ge=1, le=9)
    margin_h: int = Field(default=40, ge=0)
    margin_v: int = Field(default=220, ge=0)
    highlight_pop: bool = True
    highlight_scale: int = Field(default=110, ge=100, le=200)

    @field_validator(
        "primary_rgb", "highlight_rgb", "outline_rgb", "back_rgb", mode="before"
    )
    @classmethod
    def _coerce_rgb(cls, value: object) -> tuple[int, int, int]:
        if isinstance(value, (list, tuple)) and len(value) == 3:
            return (int(value[0]), int(value[1]), int(value[2]))
        raise ValueError(f"Expected RGB tuple, got {value!r}")

    @property
    def slug(self) -> str:
        return self.name.replace(" ", "_").lower()


class TextOverlayModel(BaseModel):
    """Standalone text overlay (title card, watermark, CTA, etc.)."""

    text: str
    kind: OverlayKind = "custom"
    start: float | None = None
    end: float | None = None
    alignment: int = Field(default=8, ge=1, le=9)
    margin_h: int = Field(default=40, ge=0)
    margin_v: int = Field(default=80, ge=0)
    font: str | None = None
    font_size: int | None = None
    primary_rgb: tuple[int, int, int] | None = None
    outline_rgb: tuple[int, int, int] | None = None
    back_rgb: tuple[int, int, int] | None = None
    primary_opacity: int = Field(default=100, ge=0, le=100)
    outline_opacity: int = Field(default=100, ge=0, le=100)
    back_opacity: int = Field(default=0, ge=0, le=100)
    outline_px: int = 4
    shadow_px: int = 0
    bold: bool = True
    italic: bool = False
    uppercase: bool = False
    border_style: int = 1
    fade_in_ms: int = Field(default=300, ge=0)
    fade_out_ms: int = Field(default=300, ge=0)

    @field_validator("primary_rgb", "outline_rgb", "back_rgb", mode="before")
    @classmethod
    def _coerce_optional_rgb(cls, value: object) -> tuple[int, int, int] | None:
        if value is None:
            return None
        if isinstance(value, (list, tuple)) and len(value) == 3:
            return (int(value[0]), int(value[1]), int(value[2]))
        raise ValueError(f"Expected RGB tuple or null, got {value!r}")


def resolve_overlay_tokens(text: str, metadata: dict[str, str] | None) -> str:
    """Replace ``{title}``, ``{channel}``, etc. in overlay text."""
    if not metadata:
        return text
    out = text
    for key, value in metadata.items():
        out = out.replace(f"{{{key}}}", str(value))
    return out
