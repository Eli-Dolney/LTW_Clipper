"""Backward-compat tests for template schema with caption styles and overlays."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.templates.models import ChannelTemplate, LookAndSound


def test_old_template_json_still_loads() -> None:
    """Templates with only caption_preset (no caption_style/overlays) remain valid."""
    data = {
        "name": "Legacy Template",
        "look": {"caption_preset": "mrbeast"},
        "hook_phrases": ["watch this"],
    }
    tpl = ChannelTemplate.model_validate(data)
    assert tpl.look.caption_preset == "mrbeast"
    assert tpl.look.caption_style is None
    assert tpl.look.overlays == []


def test_template_with_inline_style_and_overlays() -> None:
    data = {
        "name": "Styled Template",
        "look": {
            "caption_preset": "bold_outline",
            "caption_style": {
                "name": "inline",
                "font_size": 70,
                "fade_in_ms": 150,
                "primary_opacity": 90,
            },
            "overlays": [
                {"text": "{title}", "kind": "title", "alignment": 8},
                {"text": "Follow for more", "kind": "cta", "start": 0, "end": 5},
            ],
        },
    }
    tpl = ChannelTemplate.model_validate(data)
    assert tpl.look.caption_style is not None
    assert tpl.look.caption_style.font_size == 70
    assert len(tpl.look.overlays) == 2
    assert tpl.look.overlays[0].kind == "title"


def test_existing_asset_templates_load() -> None:
    templates_dir = Path(__file__).resolve().parents[1] / "assets" / "templates"
    for path in templates_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        tpl = ChannelTemplate.model_validate(data)
        assert tpl.look.caption_preset
