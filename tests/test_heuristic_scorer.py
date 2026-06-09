"""Unit tests for the deterministic highlight scorer."""

from __future__ import annotations

from src.core.ai.heuristic_scorer import HeuristicScorer
from src.core.models import Transcript, TranscriptSegment, WordTiming


def _seg(
    seg_id: int,
    start: float,
    end: float,
    text: str,
) -> TranscriptSegment:
    return TranscriptSegment(id=seg_id, start=start, end=end, text=text, words=[])


def _transcript(segments: list[TranscriptSegment]) -> Transcript:
    return Transcript(language="en", duration=segments[-1].end, segments=segments)


def test_scorer_ranks_hook_phrase_above_filler() -> None:
    transcript = _transcript([
        _seg(0, 0, 10, "So, um, we just kind of hang out here."),
        _seg(1, 10, 20, "Here's the trick that nobody talks about in this industry."),
        _seg(2, 20, 30, "Anyway, back to what I was saying."),
    ])

    scorer = HeuristicScorer(target_duration=20, min_duration=8, max_duration=60)
    scores = scorer.score_segments(transcript)

    scored_map = {s.segment.id: s.score for s in scores}
    assert scored_map[1] > scored_map[0]
    assert scored_map[1] > scored_map[2]


def test_candidates_respect_min_duration() -> None:
    transcript = _transcript([
        _seg(0, 0.0, 2.0, "Watch this!"),
        _seg(1, 2.0, 5.0, "It's the secret hack nobody talks about."),
        _seg(2, 5.0, 8.0, "You won't believe what happens next."),
    ])

    scorer = HeuristicScorer(target_duration=20, min_duration=8, max_duration=30)
    candidates = scorer.build_candidates(transcript, max_candidates=5)

    assert candidates, "Expected at least one candidate clip"
    for c in candidates:
        assert c.duration >= 8.0 - 1e-6, f"duration {c.duration} below min"


def test_candidates_do_not_overlap() -> None:
    segs = []
    base_text = "Here's why this matters and the truth about what really happens."
    for i in range(12):
        segs.append(_seg(i, i * 5.0, (i + 1) * 5.0, base_text))

    transcript = _transcript(segs)
    scorer = HeuristicScorer(target_duration=15, min_duration=10, max_duration=25)
    candidates = scorer.build_candidates(transcript, max_candidates=6)

    for a in candidates:
        overlaps = [c for c in candidates if c is not a and not (a.end <= c.start or c.end <= a.start)]
        assert not overlaps, f"candidate {a} overlaps with {overlaps}"


def test_empty_transcript_returns_empty() -> None:
    transcript = Transcript(language="en", duration=0.0, segments=[])
    scorer = HeuristicScorer()
    assert scorer.score_segments(transcript) == []
    assert scorer.build_candidates(transcript) == []
