"""Highlight engine: turn a transcript into a :class:`ClipPlan`.

Strategy (all local, all free):
1. Heuristic scorer proposes candidate clips (deterministic baseline).
2. If Ollama is available, re-rank and rewrite the top N candidates for
   titles, hooks, captions, and tags.
3. Otherwise, use simple templates to fill title/hook from the transcript
   text so the output is still immediately usable.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from ..models import ClipPlan, ClipSuggestion, MediaFeatures, Transcript
from .heuristic_scorer import (
    DEFAULT_HOOK_PHRASES,
    DEFAULT_HOOK_WORDS,
    CandidateClip,
    HeuristicScorer,
    ScoringWeights,
)
from .ollama_client import OllamaClient, OllamaConfig

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a viral short-form video editor. For each clip the user provides, write:
- "title": a 5-9 word punchy title (Title Case, no emojis, no quotes)
- "hook": a single-sentence hook that would make a viewer stop scrolling
- "caption": a 1-2 sentence caption for Shorts/TikTok
- "tags": 5-8 lowercase single-word tags
- "virality_score": 0.0-1.0 based on how strong the moment is
- "rationale": one short sentence explaining the score

Return STRICT JSON with a top-level key "clips" whose value is a list of objects,
one per input clip, in the same order."""


@dataclass
class EngineConfig:
    max_clips: int = 10
    target_duration: float = 30.0
    min_duration: float = 8.0
    max_duration: float = 60.0
    use_ollama: bool = True
    ollama: OllamaConfig | None = None
    # Niche tuning (from a channel template). When omitted, generic defaults apply.
    hook_phrases: tuple[str, ...] | None = None
    hook_words: tuple[str, ...] | None = None
    weights: ScoringWeights | None = None
    # Persona/tone block appended to the LLM system prompt for on-brand copy.
    voice_block: str = ""


class HighlightEngine:
    """Produce a :class:`ClipPlan` from a transcript (+ optional features)."""

    def __init__(self, config: EngineConfig | None = None) -> None:
        self.config = config or EngineConfig()
        self._scorer = HeuristicScorer(
            target_duration=self.config.target_duration,
            min_duration=self.config.min_duration,
            max_duration=self.config.max_duration,
            weights=self.config.weights,
            hook_phrases=self.config.hook_phrases or DEFAULT_HOOK_PHRASES,
            hook_words=self.config.hook_words or DEFAULT_HOOK_WORDS,
        )

    def _system_prompt(self) -> str:
        if self.config.voice_block.strip():
            return f"{SYSTEM_PROMPT}\n\nMatch this channel's identity:\n{self.config.voice_block.strip()}"
        return SYSTEM_PROMPT

    # ---- Public API --------------------------------------------------------

    def plan_clips(
        self,
        source_video: Path,
        transcript: Transcript,
        features: MediaFeatures | None = None,
    ) -> ClipPlan:
        candidates = self._scorer.build_candidates(
            transcript,
            features,
            max_candidates=max(self.config.max_clips * 2, 12),
        )[: self.config.max_clips]

        if not candidates:
            return ClipPlan(source_video=source_video, clips=[], generator="heuristic")

        ollama_result = None
        generator = "heuristic"

        if self.config.use_ollama:
            ollama = OllamaClient(self.config.ollama)
            if ollama.is_available():
                try:
                    ollama_result = self._enrich_with_ollama(ollama, candidates)
                    generator = "heuristic+ollama"
                except Exception as exc:  # noqa: BLE001
                    log.warning("Ollama enrichment failed, falling back: %s", exc)
                    ollama_result = None

        clips: list[ClipSuggestion] = []
        for idx, cand in enumerate(candidates):
            enriched = ollama_result[idx] if ollama_result and idx < len(ollama_result) else None
            clips.append(_to_suggestion(cand, enriched))

        clips.sort(key=lambda c: c.virality_score, reverse=True)
        return ClipPlan(source_video=source_video, clips=clips, generator=generator)

    # ---- Internals ---------------------------------------------------------

    def _enrich_with_ollama(
        self,
        client: OllamaClient,
        candidates: list[CandidateClip],
    ) -> list[dict]:
        payload = {
            "clips": [
                {
                    "index": i,
                    "duration_seconds": round(c.duration, 2),
                    "transcript": c.text[:1500],  # cap prompt size
                }
                for i, c in enumerate(candidates)
            ]
        }
        prompt = (
            "Here are candidate clips extracted from a longer video. "
            "Return a JSON object with a 'clips' array, one entry per input, preserving order.\n\n"
            + json.dumps(payload)
        )
        raw = client.generate_json(prompt, system=self._system_prompt(), temperature=0.35)
        clips = raw.get("clips", []) if isinstance(raw, dict) else []
        if not isinstance(clips, list):
            raise ValueError("Ollama response missing 'clips' list")
        return clips


# ---- Fallback / templating --------------------------------------------------

def _to_suggestion(cand: CandidateClip, llm: dict | None) -> ClipSuggestion:
    title, hook, caption, tags, score, rationale = _from_llm(llm) if llm else _from_templates(cand)

    return ClipSuggestion(
        start=cand.start,
        end=cand.end,
        title=title,
        hook=hook,
        caption=caption,
        tags=tags,
        platform_fit=_infer_platform_fit(cand.duration),
        virality_score=score,
        rationale=rationale,
        source_segment_ids=list(cand.segment_ids),
    )


def _from_llm(
    llm: dict,
) -> tuple[str, str, str, list[str], float, str]:
    title = str(llm.get("title", "")).strip()[:120]
    hook = str(llm.get("hook", "")).strip()[:280]
    caption = str(llm.get("caption", "")).strip()[:400]
    raw_tags = llm.get("tags", [])
    tags = [str(t).strip().lower().lstrip("#") for t in raw_tags if isinstance(t, (str, int))][:8]
    score = float(llm.get("virality_score", 0.5) or 0.5)
    score = max(0.0, min(1.0, score))
    rationale = str(llm.get("rationale", "")).strip()[:400]
    return title, hook, caption, tags, score, rationale


def _from_templates(
    cand: CandidateClip,
) -> tuple[str, str, str, list[str], float, str]:
    sentences = _split_sentences(cand.text)
    first = sentences[0] if sentences else cand.text[:120]
    title = _to_title_case(_truncate_words(first, 8))
    hook = first[:240]
    caption = " ".join(sentences[:2])[:360]
    tags = _extract_tags(cand.text)
    # Normalize heuristic score (usually ~0.3-0.8) onto a 0..1 band.
    score = max(0.05, min(1.0, (cand.score - 0.2) / 0.6 + 0.2))
    rationale = "Selected by heuristic scoring (audio energy, hook phrases, length fit)."
    return title, hook, caption, tags, score, rationale


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def _to_title_case(text: str) -> str:
    small = {"a", "an", "the", "and", "or", "but", "of", "for", "to", "in", "on", "at", "by", "is"}
    words = text.split()
    if not words:
        return ""
    out = []
    for i, w in enumerate(words):
        lw = w.lower().strip(".,!?\"'")
        if i != 0 and lw in small:
            out.append(lw)
        else:
            out.append(lw.capitalize() if lw else w)
    return " ".join(out).strip(".,!?\"'")


def _truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _extract_tags(text: str, limit: int = 6) -> list[str]:
    stop = _STOPWORDS
    tokens = re.findall(r"[a-zA-Z]{4,}", text.lower())
    freq: dict[str, int] = {}
    for t in tokens:
        if t in stop:
            continue
        freq[t] = freq.get(t, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)
    return [t for t, _ in ranked[:limit]]


def _infer_platform_fit(duration: float) -> list:
    if duration <= 60:
        return ["youtube_shorts", "tiktok", "instagram_reels"]
    return ["youtube"]


_STOPWORDS = frozenset(
    """
    about above after again against all also amongst another been because before being
    below between both could does doing down during each ever every from have having
    here into itself just like making many more most much must never only other over
    said same should since some something sometimes still such take than that their
    them then there these they this those through today together took very want ways
    were what when where which while with would your yourself about above
    actually always around because becomes being could didn't doesn't done enough even
    every gets getting goes going gonna gotta isn't it's know looks maybe means might
    really saying sees seen should's something's there's thing things usually wanted
    wasn't weren't won't yeah that's they're doesn't isn't there's here's he's she's
    """.split()
)
