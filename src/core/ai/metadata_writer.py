"""Produce publish-ready metadata for a clip.

Given a :class:`ClipSuggestion` and the source :class:`Transcript`, emit
:class:`ClipMetadata` with YouTube description + chapters, hashtag sets for
Shorts/TikTok, and a thumbnail headline.

If Ollama is available we let it polish titles and descriptions; otherwise
we fall back to templates derived from the transcript text.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from ..models import (
    ClipMetadata,
    ClipSuggestion,
    ShortsMetadata,
    Transcript,
    YouTubeMetadata,
)
from .ollama_client import OllamaClient, OllamaConfig

log = logging.getLogger(__name__)


METADATA_SYSTEM_PROMPT = """You write YouTube metadata for short-form creators.
Return STRICT JSON with these keys:
- "youtube_title": <=90 chars, punchy, no clickbait all caps
- "youtube_description": 2-4 short paragraphs, include a one-line summary first
- "youtube_tags": 8-15 lowercase single-word or two-word tags, no # symbol
- "thumbnail_text": 2-4 word hook for thumbnail overlay, Title Case
- "shorts_caption": 1-2 sentences <=220 chars
- "shorts_hashtags": 5-10 hashtags, lowercase, with # prefix
No markdown, no commentary, just the JSON object."""


@dataclass
class MetadataConfig:
    use_ollama: bool = True
    ollama: OllamaConfig | None = None
    # Niche voice (from a channel template) appended to the LLM system prompt.
    voice_block: str = ""
    # Hashtags ("#ai") and keyword tags always merged into a clip's output.
    extra_hashtags: list[str] | None = None
    extra_tags: list[str] | None = None

    def system_prompt(self) -> str:
        if self.voice_block.strip():
            return f"{METADATA_SYSTEM_PROMPT}\n\nMatch this channel's identity:\n{self.voice_block.strip()}"
        return METADATA_SYSTEM_PROMPT


class MetadataWriter:
    """Builds a :class:`ClipMetadata` for a clip."""

    def __init__(self, config: MetadataConfig | None = None) -> None:
        self.config = config or MetadataConfig()

    def build(
        self,
        clip: ClipSuggestion,
        transcript: Transcript,
        *,
        source_title: str | None = None,
    ) -> ClipMetadata:
        slug = _slugify(clip.title or f"clip_{int(clip.start)}")
        chapters = _build_chapters(transcript, clip)

        llm_data: dict | None = None
        if self.config.use_ollama:
            client = OllamaClient(self.config.ollama)
            if client.is_available():
                try:
                    llm_data = self._ask_ollama(client, clip, source_title)
                except Exception as exc:  # noqa: BLE001
                    log.warning("Ollama metadata call failed: %s", exc)
                    llm_data = None

        extra_tags = self.config.extra_tags or []
        extra_hashtags = self.config.extra_hashtags or []

        if llm_data:
            yt = YouTubeMetadata(
                title=_clamp(str(llm_data.get("youtube_title", clip.title)), 95),
                description=str(llm_data.get("youtube_description", _fallback_description(clip))),
                tags=_merge_tags(_clean_tags(llm_data.get("youtube_tags", clip.tags)), extra_tags),
                chapters=chapters,
            )
            shorts = ShortsMetadata(
                caption=_clamp(str(llm_data.get("shorts_caption", clip.caption)), 220),
                hashtags=_merge_hashtags(
                    _clean_hashtags(llm_data.get("shorts_hashtags", []), fallback=clip.tags),
                    extra_hashtags,
                ),
                platforms=list(clip.platform_fit),
            )
            thumbnail_text = _clamp(str(llm_data.get("thumbnail_text", clip.hook[:40])), 40)
        else:
            yt = YouTubeMetadata(
                title=clip.title,
                description=_fallback_description(clip),
                tags=_merge_tags(list(clip.tags), extra_tags),
                chapters=chapters,
            )
            shorts = ShortsMetadata(
                caption=clip.caption or clip.hook,
                hashtags=_merge_hashtags([f"#{t}" for t in clip.tags[:6]], extra_hashtags),
                platforms=list(clip.platform_fit),
            )
            thumbnail_text = _thumbnail_from_hook(clip.hook or clip.title)

        return ClipMetadata(
            slug=slug,
            start=clip.start,
            end=clip.end,
            virality_score=clip.virality_score,
            rationale=clip.rationale,
            thumbnail_text=thumbnail_text,
            youtube=yt,
            shorts=shorts,
        )

    # ---- Ollama prompt -----------------------------------------------------

    def _ask_ollama(
        self,
        client: OllamaClient,
        clip: ClipSuggestion,
        source_title: str | None,
    ) -> dict:
        context = {
            "source_title": source_title or "",
            "clip_title": clip.title,
            "clip_hook": clip.hook,
            "clip_caption": clip.caption,
            "clip_tags": clip.tags,
            "platform_fit": clip.platform_fit,
            "virality_score": clip.virality_score,
            "rationale": clip.rationale,
        }
        prompt = (
            "Write publish-ready metadata for this clip. Context:\n"
            + _pretty_json(context)
        )
        result = client.generate_json(prompt, system=self.config.system_prompt(), temperature=0.4)
        return result if isinstance(result, dict) else {}


# ---- Helpers ---------------------------------------------------------------

def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:60] or "clip"


def _clamp(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _fallback_description(clip: ClipSuggestion) -> str:
    parts = []
    if clip.hook:
        parts.append(clip.hook.strip())
    if clip.caption and clip.caption.strip() != clip.hook.strip():
        parts.append(clip.caption.strip())
    tags_line = " ".join(f"#{t}" for t in clip.tags[:6])
    if tags_line:
        parts.append(tags_line)
    parts.append("— clipped with LTW Video Splitter Pro (local & free).")
    return "\n\n".join(parts)


def _clean_tags(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for t in raw:
        if not isinstance(t, (str, int)):
            continue
        clean = re.sub(r"[^a-zA-Z0-9 \-]", "", str(t)).strip().lower()
        if clean and clean not in out:
            out.append(clean)
    return out[:15]


def _clean_hashtags(raw, *, fallback: list[str]) -> list[str]:
    if not isinstance(raw, list):
        raw = []
    out: list[str] = []
    for t in raw:
        if not isinstance(t, str):
            continue
        tag = t.strip()
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = "#" + tag.lstrip("#")
        tag = re.sub(r"[^#a-zA-Z0-9_]", "", tag).lower()
        if tag != "#" and tag not in out:
            out.append(tag)
    if not out:
        out = [f"#{t}" for t in fallback[:6]]
    return out[:12]


def _merge_tags(base: list[str], extra: list[str], *, limit: int = 15) -> list[str]:
    """Append niche keyword tags, deduped, preserving order, capped."""
    out = list(base)
    for t in extra:
        clean = re.sub(r"[^a-zA-Z0-9 \-]", "", str(t)).strip().lower()
        if clean and clean not in out:
            out.append(clean)
    return out[:limit]


def _merge_hashtags(base: list[str], extra: list[str], *, limit: int = 12) -> list[str]:
    out = list(base)
    for t in extra:
        tag = str(t).strip()
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = "#" + tag.lstrip("#")
        tag = re.sub(r"[^#a-zA-Z0-9_]", "", tag).lower()
        if tag != "#" and tag not in out:
            out.append(tag)
    return out[:limit]


def _thumbnail_from_hook(hook: str) -> str:
    words = re.findall(r"[A-Za-z0-9']+", hook)[:4]
    if not words:
        return "Watch This"
    return " ".join(w.capitalize() for w in words)


def _build_chapters(transcript: Transcript, clip: ClipSuggestion) -> list[tuple[float, str]]:
    """For long-form uploads, pull a handful of chapter markers within the clip window."""
    chapters: list[tuple[float, str]] = []
    window = [
        s for s in transcript.segments
        if s.end > clip.start and s.start < clip.end
    ]
    if not window:
        return chapters
    step = max(1, len(window) // 5)
    for seg in window[::step][:6]:
        title = _clamp(seg.text.strip().split(".")[0], 50)
        chapters.append((round(seg.start - clip.start, 1), title))
    return chapters


def _pretty_json(obj) -> str:
    import json as _json
    return _json.dumps(obj, indent=2, ensure_ascii=False)
