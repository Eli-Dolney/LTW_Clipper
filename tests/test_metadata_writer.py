"""Tests for the metadata writer's offline template path."""

from __future__ import annotations

from src.core.ai.metadata_writer import MetadataConfig, MetadataWriter
from src.core.models import (
    ClipSuggestion,
    Transcript,
    TranscriptSegment,
)


def _transcript() -> Transcript:
    return Transcript(
        language="en",
        duration=60.0,
        segments=[
            TranscriptSegment(id=0, start=0, end=20, text="Intro explaining the setup.", words=[]),
            TranscriptSegment(id=1, start=20, end=40, text="The core trick in detail.", words=[]),
            TranscriptSegment(id=2, start=40, end=60, text="Final takeaways for creators.", words=[]),
        ],
    )


def test_metadata_without_ollama_is_usable() -> None:
    clip = ClipSuggestion(
        start=15.0,
        end=45.0,
        title="The Trick Nobody Talks About",
        hook="Here's the single trick that changes everything for new creators.",
        caption="This one move doubled my retention overnight.",
        tags=["youtube", "shorts", "creator", "retention", "editing"],
        virality_score=0.78,
        rationale="Strong hook phrase + mid-segment energy peak.",
        platform_fit=["youtube_shorts", "tiktok"],
    )

    writer = MetadataWriter(MetadataConfig(use_ollama=False))
    meta = writer.build(clip, _transcript(), source_title="Ultimate Creator Guide")

    assert meta.slug, "slug should be non-empty"
    assert meta.youtube.title == clip.title
    assert meta.youtube.description, "description should be populated"
    assert len(meta.youtube.tags) >= 3
    assert meta.shorts.hashtags, "hashtags should exist"
    assert all(h.startswith("#") for h in meta.shorts.hashtags)
    assert len(meta.thumbnail_text.split()) <= 4
    # Chapters should include at least one marker inside the clip window.
    assert any(0.0 <= offset <= (clip.end - clip.start) for offset, _ in meta.youtube.chapters)
