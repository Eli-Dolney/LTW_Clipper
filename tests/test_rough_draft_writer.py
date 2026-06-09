"""Tests for rough draft export."""

from __future__ import annotations

from pathlib import Path

from src.core.ai.rough_draft_writer import write_rough_draft
from src.core.models import ClipPlan, ClipSuggestion, Transcript, TranscriptSegment


def test_write_rough_draft(tmp_path: Path) -> None:
    transcript = Transcript(
        language="en",
        duration=60.0,
        segments=[
            TranscriptSegment(id=0, start=0.0, end=5.0, text="Hello world"),
            TranscriptSegment(id=1, start=5.0, end=10.0, text="Second line"),
        ],
    )
    plan = ClipPlan(
        source_video=Path("video.mp4"),
        clips=[
            ClipSuggestion(start=0.0, end=8.0, title="Opening hook", hook="Watch this"),
        ],
    )
    out = write_rough_draft(tmp_path, transcript=transcript, plan=plan, source_title="Demo")
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "Rough Draft" in text
    assert "Hello world" in text
    assert "Opening hook" in text
    assert (tmp_path / "transcript.txt").is_file()
