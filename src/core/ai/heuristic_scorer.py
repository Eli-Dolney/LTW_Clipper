"""Deterministic, always-on highlight scoring.

Combines signals that don't require any external service:
- audio energy (RMS peaks) from transcript segments or features
- transcript content (keyword/phrase hits, sentence completeness)
- segment length (prefer punchy, not too short / too long)

This is the baseline. If Ollama is available, the highlight engine re-ranks
and rewrites the top N candidates; otherwise it uses the raw heuristic ranks.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Iterable

from ..models import MediaFeatures, Transcript, TranscriptSegment

log = logging.getLogger(__name__)


# Phrases and cues that tend to mark high-retention moments in long-form content.
DEFAULT_HOOK_PHRASES = (
    "here's the trick", "here's why", "watch this", "the secret",
    "you won't believe", "the truth is", "nobody talks about",
    "the biggest mistake", "wait", "stop", "let me show you",
    "the crazy part", "here's the thing", "plot twist",
    "what happened next", "the real reason", "the best part",
)

DEFAULT_HOOK_WORDS = (
    "secret", "truth", "mistake", "crazy", "insane", "shocking",
    "wait", "stop", "listen", "watch", "never", "always",
    "why", "how", "trick", "hack", "reason",
)


@dataclass
class ScoringWeights:
    audio: float = 0.25
    hook_phrase: float = 0.35
    hook_word: float = 0.15
    length: float = 0.15
    completeness: float = 0.10


@dataclass
class ScoredSegment:
    segment: TranscriptSegment
    score: float
    breakdown: dict[str, float] = field(default_factory=dict)


@dataclass
class CandidateClip:
    """A proposed clip built from one or more transcript segments."""

    start: float
    end: float
    text: str
    score: float
    segment_ids: list[int]
    features: dict[str, float] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class HeuristicScorer:
    """Scores transcript segments and groups them into candidate clips."""

    def __init__(
        self,
        *,
        target_duration: float = 30.0,
        min_duration: float = 8.0,
        max_duration: float = 60.0,
        weights: ScoringWeights | None = None,
        hook_phrases: Iterable[str] = DEFAULT_HOOK_PHRASES,
        hook_words: Iterable[str] = DEFAULT_HOOK_WORDS,
    ) -> None:
        self.target_duration = float(target_duration)
        self.min_duration = float(min_duration)
        self.max_duration = float(max_duration)
        self.weights = weights or ScoringWeights()
        self._phrases = tuple(p.lower() for p in hook_phrases)
        self._words = tuple(w.lower() for w in hook_words)

    # ---- Public API --------------------------------------------------------

    def score_segments(
        self,
        transcript: Transcript,
        features: MediaFeatures | None = None,
    ) -> list[ScoredSegment]:
        """Score every transcript segment individually (0..1)."""
        scored: list[ScoredSegment] = []
        audio_lookup = _audio_lookup(features)

        for seg in transcript.segments:
            text_lc = seg.text.lower()
            audio = _audio_energy_for(seg, audio_lookup)
            phrase_hits = _count_phrase_hits(text_lc, self._phrases)
            word_hits = _count_word_hits(text_lc, self._words)
            length_fit = _length_fit(seg.duration(), self.target_duration, self.max_duration)
            completeness = _completeness(seg.text)

            breakdown = {
                "audio": audio,
                "hook_phrase": min(1.0, phrase_hits / 2.0),
                "hook_word": min(1.0, word_hits / 4.0),
                "length": length_fit,
                "completeness": completeness,
            }
            total = (
                self.weights.audio * breakdown["audio"]
                + self.weights.hook_phrase * breakdown["hook_phrase"]
                + self.weights.hook_word * breakdown["hook_word"]
                + self.weights.length * breakdown["length"]
                + self.weights.completeness * breakdown["completeness"]
            )
            scored.append(ScoredSegment(segment=seg, score=round(total, 4), breakdown=breakdown))

        return scored

    def build_candidates(
        self,
        transcript: Transcript,
        features: MediaFeatures | None = None,
        *,
        max_candidates: int = 25,
    ) -> list[CandidateClip]:
        """Group segments into clip-sized candidates and rank them.

        Algorithm (deliberately simple / deterministic):
        1. Score every segment.
        2. For each segment with score >= threshold, expand forward and
           backward by adjacent segments until we hit ``target_duration``
           (or no more context is available).
        3. Dedupe overlapping windows, keep the higher-scoring one.
        4. Sort by aggregate score, return top ``max_candidates``.
        """
        scored = self.score_segments(transcript, features)
        if not scored:
            return []

        # Threshold auto-tunes to the 60th percentile so we always get
        # some candidates even on low-energy content.
        sorted_scores = sorted((s.score for s in scored), reverse=True)
        cutoff_idx = max(0, int(len(sorted_scores) * 0.4) - 1)
        threshold = sorted_scores[cutoff_idx] if sorted_scores else 0.0

        scored_by_id = {s.segment.id: s for s in scored}
        ordered = sorted(scored, key=lambda x: x.segment.start)
        id_to_index = {s.segment.id: i for i, s in enumerate(ordered)}

        raw_candidates: list[CandidateClip] = []
        for s in scored:
            if s.score < threshold:
                continue
            window = self._expand_window(s.segment, ordered, id_to_index, scored_by_id)
            if window is None:
                continue
            raw_candidates.append(window)

        # Deduplicate overlapping windows (keep highest-scoring).
        raw_candidates.sort(key=lambda c: c.score, reverse=True)
        chosen: list[CandidateClip] = []
        for cand in raw_candidates:
            if any(_overlaps(cand, other) for other in chosen):
                continue
            chosen.append(cand)
            if len(chosen) >= max_candidates:
                break

        chosen.sort(key=lambda c: c.score, reverse=True)
        return chosen

    # ---- Internal helpers --------------------------------------------------

    def _expand_window(
        self,
        seed: TranscriptSegment,
        ordered: list[ScoredSegment],
        id_to_index: dict[int, int],
        scored_by_id: dict[int, ScoredSegment],
    ) -> CandidateClip | None:
        idx = id_to_index.get(seed.id)
        if idx is None:
            return None

        start = seed.start
        end = seed.end
        included: list[int] = [seed.id]
        score_sum = scored_by_id[seed.id].score
        left = idx - 1
        right = idx + 1

        while (end - start) < self.target_duration:
            add_right = (
                right < len(ordered)
                and (ordered[right].segment.end - start) <= self.max_duration
            )
            add_left = (
                left >= 0
                and (end - ordered[left].segment.start) <= self.max_duration
            )

            if not add_right and not add_left:
                break

            # Prefer the neighbor with higher score to keep quality high.
            right_score = ordered[right].score if add_right else -1.0
            left_score = ordered[left].score if add_left else -1.0
            if right_score >= left_score and add_right:
                end = ordered[right].segment.end
                included.append(ordered[right].segment.id)
                score_sum += ordered[right].score
                right += 1
            elif add_left:
                start = ordered[left].segment.start
                included.append(ordered[left].segment.id)
                score_sum += ordered[left].score
                left -= 1
            else:
                break

        duration = end - start
        if duration < self.min_duration:
            return None

        text = " ".join(scored_by_id[i].segment.text for i in sorted(included)).strip()
        avg_score = score_sum / max(1, len(included))

        return CandidateClip(
            start=round(start, 3),
            end=round(end, 3),
            text=text,
            score=round(avg_score, 4),
            segment_ids=sorted(included),
        )


# ---- Free functions --------------------------------------------------------

def _audio_lookup(features: MediaFeatures | None) -> list[tuple[float, float, float]]:
    if features is None:
        return []
    return [(w.start, w.end, w.rms) for w in features.audio]


def _audio_energy_for(
    seg: TranscriptSegment,
    audio: list[tuple[float, float, float]],
) -> float:
    """Return normalized [0,1] mean RMS across the segment window."""
    if not audio:
        return 0.5  # neutral prior when we have no audio features
    max_rms = max((rms for _, _, rms in audio), default=1.0) or 1.0
    total = 0.0
    count = 0
    for start, end, rms in audio:
        if end < seg.start or start > seg.end:
            continue
        total += rms
        count += 1
    if count == 0:
        return 0.5
    return min(1.0, (total / count) / max_rms)


def _count_phrase_hits(text_lc: str, phrases: tuple[str, ...]) -> int:
    return sum(1 for p in phrases if p in text_lc)


def _count_word_hits(text_lc: str, words: tuple[str, ...]) -> int:
    tokens = set(re.findall(r"[a-z']+", text_lc))
    return sum(1 for w in words if w in tokens)


def _length_fit(duration: float, target: float, cap: float) -> float:
    """Triangle-shaped score peaking at ``target`` seconds."""
    if duration <= 0:
        return 0.0
    if duration >= cap:
        return max(0.0, 1.0 - (duration - cap) / cap)
    if duration <= target:
        return duration / target
    return max(0.0, 1.0 - (duration - target) / max(1.0, (cap - target)))


def _completeness(text: str) -> float:
    """Higher when the segment reads like a finished thought."""
    stripped = text.strip()
    if not stripped:
        return 0.0
    ends_punct = 1.0 if stripped[-1] in ".!?" else 0.3
    starts_cap = 1.0 if stripped[0].isupper() else 0.5
    word_count = len(stripped.split())
    length_ok = 1.0 if 6 <= word_count <= 80 else 0.5
    return (ends_punct + starts_cap + length_ok) / 3.0


def _overlaps(a: CandidateClip, b: CandidateClip, pad: float = 0.5) -> bool:
    return not (a.end + pad <= b.start or b.end + pad <= a.start)
