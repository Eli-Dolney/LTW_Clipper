"""Tests for caption style manager."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.captions.models import CaptionStyleModel
from src.core.captions.style_manager import StyleManager


def test_loads_builtin_json_styles() -> None:
    mgr = StyleManager()
    names = mgr.names()
    assert "bold_outline" in names
    assert "hormozi" in names
    assert "neon" in names


def test_save_and_delete_custom_style(tmp_path: Path) -> None:
    mgr = StyleManager(styles_dir=tmp_path)
    style = CaptionStyleModel(name="My Custom", font_size=48, builtin=False)
    mgr.save(style)
    assert mgr.get("My Custom") is not None
    assert (tmp_path / "my_custom.json").is_file()
    assert mgr.delete("My Custom")
    assert mgr.get("My Custom") is None


def test_import_export_round_trip(tmp_path: Path) -> None:
    mgr = StyleManager(styles_dir=tmp_path)
    style = CaptionStyleModel(name="Export Me", fade_in_ms=250, alignment=8)
    mgr.save(style)
    dest = tmp_path / "exported.json"
    assert mgr.export("Export Me", dest)
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["fade_in_ms"] == 250
    assert data["alignment"] == 8


def test_resolve_prefers_inline_style() -> None:
    mgr = StyleManager()
    inline = CaptionStyleModel(name="inline", font_size=99)
    resolved = mgr.resolve("bold_outline", inline)
    assert resolved.font_size == 99


def test_duplicate_creates_copy(tmp_path: Path) -> None:
    mgr = StyleManager(styles_dir=tmp_path)
    base = CaptionStyleModel(name="Base Style", builtin=False)
    mgr.save(base)
    dup = mgr.duplicate("Base Style", "Base Style Copy")
    assert dup is not None
    assert dup.name == "Base Style Copy"
    assert dup.builtin is False
