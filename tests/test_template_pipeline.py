"""Tests that channel templates actually flow into the scoring + metadata stages."""

from __future__ import annotations

from pathlib import Path

from src.core.ai.heuristic_scorer import ScoringWeights
from src.core.ai.highlight_engine import EngineConfig, HighlightEngine
from src.core.ai.metadata_writer import MetadataConfig, MetadataWriter
from src.core.models import ClipSuggestion, Transcript, TranscriptSegment
from src.core.opus_clip_processor import PipelineOptions
from src.core.templates import TemplateManager

BUILTIN_DIR = Path(__file__).resolve().parents[1] / "assets" / "templates"


def _seg(i: int, start: float, end: float, text: str) -> TranscriptSegment:
    return TranscriptSegment(id=i, start=start, end=end, text=text, words=[])


def test_from_template_maps_fields() -> None:
    gaming = TemplateManager(BUILTIN_DIR).get("Gaming")
    assert gaming is not None
    opts = PipelineOptions.from_template(gaming, use_ollama=False, whisper_model="tiny")

    assert opts.template_name == "Gaming"
    assert opts.caption_preset == gaming.look.caption_preset
    assert opts.max_clips == gaming.max_clips
    assert opts.scoring_weights["audio"] == gaming.scoring_weights.audio
    assert opts.hook_phrases and "no way" in opts.hook_phrases
    # overrides win over template
    assert opts.use_ollama is False
    assert opts.whisper_model == "tiny"
    # niche hashtags flow to metadata extras
    assert "#gaming" in (opts.extra_hashtags or [])


def test_template_hooks_change_ranking() -> None:
    # A segment that only a gamedev template would consider a strong hook.
    transcript = Transcript(
        language="en",
        duration=30,
        segments=[
            _seg(0, 0, 10, "Anyway so we just sat around chatting for a while."),
            _seg(1, 10, 20, "Let me show you how to set up the blueprint node for collision."),
            _seg(2, 20, 30, "And that's pretty much it for today."),
        ],
    )

    gamedev = TemplateManager(BUILTIN_DIR).get("Game Dev Tutorial")
    assert gamedev is not None

    engine = HighlightEngine(
        EngineConfig(
            use_ollama=False,
            hook_phrases=tuple(gamedev.hook_phrases),
            hook_words=tuple(gamedev.hook_words),
            weights=ScoringWeights(**gamedev.scoring_weights.as_dict()),
            target_duration=20,
            min_duration=8,
            max_duration=40,
        )
    )
    scores = engine._scorer.score_segments(transcript)
    by_id = {s.segment.id: s.score for s in scores}
    assert by_id[1] > by_id[0]
    assert by_id[1] > by_id[2]


def test_metadata_merges_niche_hashtags_and_tags() -> None:
    clip = ClipSuggestion(
        start=0.0,
        end=20.0,
        title="Test Clip",
        hook="Here is the hook",
        caption="A caption",
        tags=["alpha", "beta"],
        platform_fit=["youtube_shorts"],
        virality_score=0.5,
    )
    transcript = Transcript(language="en", duration=20, segments=[_seg(0, 0, 20, "Hello world.")])

    writer = MetadataWriter(
        MetadataConfig(
            use_ollama=False,
            extra_hashtags=["#ai", "#tech"],
            extra_tags=["artificial intelligence"],
        )
    )
    meta = writer.build(clip, transcript)
    assert "#ai" in meta.shorts.hashtags
    assert "artificial intelligence" in meta.youtube.tags
    # original tags still present
    assert "alpha" in meta.youtube.tags


def test_voice_block_injected_into_prompts() -> None:
    cfg = MetadataConfig(use_ollama=False, voice_block="Channel persona: Test persona")
    assert "Test persona" in cfg.system_prompt()

    eng = HighlightEngine(EngineConfig(use_ollama=False, voice_block="Voice / tone: hype"))
    assert "hype" in eng._system_prompt()
