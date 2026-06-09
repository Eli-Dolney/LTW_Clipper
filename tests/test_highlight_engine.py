"""Tests for the highlight engine with Ollama disabled (deterministic path)."""

from __future__ import annotations

from pathlib import Path

from src.core.ai.highlight_engine import EngineConfig, HighlightEngine
from src.core.models import Transcript, TranscriptSegment


def _seg(i: int, start: float, end: float, text: str) -> TranscriptSegment:
    return TranscriptSegment(id=i, start=start, end=end, text=text, words=[])


def _long_transcript() -> Transcript:
    snippets = [
        "Welcome back everyone. Today I want to talk about something wild.",
        "Here's the trick that actually works for this problem.",
        "Most people completely skip this step, which is the biggest mistake you can make.",
        "Watch this carefully, because it changes everything.",
        "Honestly, nobody talks about this for some reason.",
        "Anyway, back to the main topic.",
        "Let me show you exactly how to set this up in under a minute.",
        "The truth is it's way easier than the internet makes it seem.",
    ]
    segs = []
    for i, s in enumerate(snippets):
        segs.append(_seg(i, i * 10.0, (i + 1) * 10.0, s))
    return Transcript(language="en", duration=80.0, segments=segs)


def test_plan_clips_produces_suggestions_without_ollama(tmp_path: Path) -> None:
    engine = HighlightEngine(EngineConfig(
        max_clips=3,
        target_duration=20,
        min_duration=8,
        max_duration=40,
        use_ollama=False,
    ))
    plan = engine.plan_clips(tmp_path / "video.mp4", _long_transcript())

    assert plan.generator == "heuristic"
    assert 1 <= len(plan.clips) <= 3
    for clip in plan.clips:
        assert clip.end > clip.start
        assert clip.title, "template fallback should produce a title"
        assert 0.0 <= clip.virality_score <= 1.0
        assert clip.platform_fit


def test_plan_clips_sorted_by_score(tmp_path: Path) -> None:
    engine = HighlightEngine(EngineConfig(
        max_clips=5,
        target_duration=20,
        min_duration=8,
        max_duration=40,
        use_ollama=False,
    ))
    plan = engine.plan_clips(tmp_path / "video.mp4", _long_transcript())

    scores = [c.virality_score for c in plan.clips]
    assert scores == sorted(scores, reverse=True)
