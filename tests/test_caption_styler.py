"""Tests for ASS/SRT/VTT caption generation (no ffmpeg needed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.captions.models import CaptionStyleModel, TextOverlayModel, resolve_overlay_tokens
from src.core.captions.styler import (
    CAPTION_PRESETS,
    CaptionStyler,
    _ass_time,
    _opacity_to_ass_alpha,
    _rgb_to_ass_bgr,
    _srt_time,
    _vtt_time,
    _wrap_text,
)
from src.core.models import Transcript, TranscriptSegment, WordTiming


def _transcript() -> Transcript:
    words = [
        WordTiming(word="Here's", start=0.0, end=0.5, probability=1.0),
        WordTiming(word="the", start=0.5, end=0.7, probability=1.0),
        WordTiming(word="trick", start=0.7, end=1.2, probability=1.0),
        WordTiming(word="nobody", start=1.2, end=1.8, probability=1.0),
        WordTiming(word="talks", start=1.8, end=2.2, probability=1.0),
        WordTiming(word="about.", start=2.2, end=2.8, probability=1.0),
    ]
    seg = TranscriptSegment(
        id=0,
        start=0.0,
        end=2.8,
        text="Here's the trick nobody talks about.",
        words=words,
    )
    return Transcript(language="en", duration=2.8, segments=[seg])


def test_srt_time_formats() -> None:
    assert _srt_time(0.0) == "00:00:00,000"
    assert _srt_time(1.234) == "00:00:01,234"
    assert _srt_time(3661.5) == "01:01:01,500"


def test_vtt_time_uses_dot() -> None:
    assert _vtt_time(1.234) == "00:00:01.234"


def test_ass_time_compact() -> None:
    assert _ass_time(0) == "0:00:00.00"
    assert _ass_time(65.5) == "0:01:05.50"


def test_rgb_to_ass_is_bgr_hex() -> None:
    assert _rgb_to_ass_bgr((255, 0, 0)) == "&H000000FF"


def test_rgb_to_ass_with_opacity() -> None:
    # 50% opacity -> alpha byte 0x80
    assert _rgb_to_ass_bgr((255, 255, 255), 50) == "&H80FFFFFF"


def test_opacity_to_ass_alpha_mapping() -> None:
    assert _opacity_to_ass_alpha(100) == 0
    assert _opacity_to_ass_alpha(0) == 255


def test_wrap_text_respects_limit() -> None:
    text = "This is a fairly long caption sentence."
    wrapped = _wrap_text(text, max_chars=10)
    for line in wrapped.splitlines():
        assert len(line) <= 20


def test_styler_writes_all_formats(tmp_path: Path) -> None:
    styler = CaptionStyler("bold_outline")
    arts = styler.write(_transcript(), tmp_path, base_name="clip")
    assert arts.ass and arts.ass.exists()
    assert arts.srt and arts.srt.exists()
    assert arts.vtt and arts.vtt.exists()

    ass_content = arts.ass.read_text(encoding="utf-8")
    assert "[Script Info]" in ass_content
    assert "Dialogue:" in ass_content
    assert "\\k" in ass_content

    srt_content = arts.srt.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:02,800" in srt_content

    vtt_content = arts.vtt.read_text(encoding="utf-8")
    assert vtt_content.startswith("WEBVTT")


def test_clip_offset_shifts_and_filters(tmp_path: Path) -> None:
    full = Transcript(
        language="en",
        duration=10.0,
        segments=[
            TranscriptSegment(id=0, start=0.0, end=3.0, text="Intro.", words=[]),
            TranscriptSegment(id=1, start=3.0, end=6.0, text="Middle.", words=[]),
            TranscriptSegment(id=2, start=6.0, end=10.0, text="End.", words=[]),
        ],
    )
    styler = CaptionStyler("minimal")
    arts = styler.write(full, tmp_path, base_name="clip", clip_offset=3.0, clip_end=6.0)
    srt = arts.srt.read_text(encoding="utf-8")
    assert "Middle." in srt
    assert "Intro." not in srt
    assert "End." not in srt
    assert "00:00:00,000 --> 00:00:03,000" in srt


def test_all_presets_instantiate() -> None:
    for name in CAPTION_PRESETS:
        styler = CaptionStyler(name)
        assert styler.style.name == name


def test_unknown_preset_raises() -> None:
    with pytest.raises(ValueError):
        CaptionStyler("nonexistent_preset_zzz")


def test_fade_tags_in_ass(tmp_path: Path) -> None:
    style = CaptionStyleModel(name="fade_test", fade_in_ms=300, fade_out_ms=200)
    styler = CaptionStyler(style)
    ass = styler.write(_transcript(), tmp_path, formats=("ass",)).ass
    content = ass.read_text(encoding="utf-8")
    assert r"{\fad(300,200)}" in content


def test_alignment_in_ass_header(tmp_path: Path) -> None:
    style = CaptionStyleModel(name="align_test", alignment=8, margin_h=60, margin_v=100)
    styler = CaptionStyler(style)
    ass = styler.write(_transcript(), tmp_path, formats=("ass",)).ass
    content = ass.read_text(encoding="utf-8")
    assert ",8,60,60,100,1" in content


def test_opacity_alpha_in_ass_header(tmp_path: Path) -> None:
    style = CaptionStyleModel(
        name="opacity_test",
        primary_rgb=(255, 255, 255),
        primary_opacity=50,
    )
    styler = CaptionStyler(style)
    ass = styler.write(_transcript(), tmp_path, formats=("ass",)).ass
    content = ass.read_text(encoding="utf-8")
    assert "&H80FFFFFF" in content


def test_highlight_pop_tag(tmp_path: Path) -> None:
    style = CaptionStyleModel(
        name="pop_test",
        highlight_pop=True,
        highlight_scale=125,
    )
    styler = CaptionStyler(style)
    ass = styler.write(_transcript(), tmp_path, formats=("ass",)).ass
    content = ass.read_text(encoding="utf-8")
    assert r"\fscx125\fscy125" in content


def test_overlay_events_emitted(tmp_path: Path) -> None:
    overlays = [
        TextOverlayModel(text="{title}", kind="title", alignment=8, fade_in_ms=200),
        TextOverlayModel(text="Subscribe!", kind="cta", alignment=2, start=1.0, end=2.5),
    ]
    styler = CaptionStyler("bold_outline")
    arts = styler.write(
        _transcript(), tmp_path,
        formats=("ass",),
        overlays=overlays,
        overlay_metadata={"title": "My Great Clip"},
        clip_duration=3.0,
    )
    content = arts.ass.read_text(encoding="utf-8")
    assert "Style: Overlay0" in content
    assert "Style: Overlay1" in content
    assert "My Great Clip" in content
    assert "Subscribe!" in content
    assert r"{\fad(200," in content


def test_resolve_overlay_tokens() -> None:
    assert resolve_overlay_tokens("{title} by {channel}", {"title": "Hi", "channel": "LTW"}) == "Hi by LTW"


def test_build_preview_ass() -> None:
    styler = CaptionStyler("bold_outline")
    ass = styler.build_preview_ass(sample_text="Preview caption text")
    assert "Preview caption text" in ass or "PREVIEW" in ass.upper()
    assert "Dialogue:" in ass


def test_style_model_round_trip() -> None:
    original = CaptionStyleModel(
        name="custom",
        font_size=55,
        primary_opacity=80,
        fade_in_ms=100,
        alignment=5,
    )
    data = original.model_dump(mode="json")
    restored = CaptionStyleModel.model_validate(data)
    assert restored.name == "custom"
    assert restored.primary_opacity == 80
    assert restored.alignment == 5
