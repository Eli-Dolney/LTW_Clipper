"""Pydantic models for channel templates.

These are the stable, serializable contract for a niche template. The pipeline
reads them but never writes them; the GUI / :class:`TemplateManager` own writes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..models import Platform

ContentType = Literal["clips", "shorts", "tutorial", "long_form", "gaming"]


class ScoringWeightsModel(BaseModel):
    """Mirror of :class:`heuristic_scorer.ScoringWeights` (serializable).

    Weights are relative; they don't need to sum to 1.0 but conventionally do.
    """

    audio: float = 0.25
    hook_phrase: float = 0.35
    hook_word: float = 0.15
    length: float = 0.15
    completeness: float = 0.10

    def as_dict(self) -> dict[str, float]:
        return {
            "audio": self.audio,
            "hook_phrase": self.hook_phrase,
            "hook_word": self.hook_word,
            "length": self.length,
            "completeness": self.completeness,
        }


class VoiceProfile(BaseModel):
    """Drives metadata tone (titles, descriptions, captions, hashtags)."""

    persona: str = ""
    tone: str = ""
    title_style: str = ""
    cta: str = ""
    # Hashtags always appended to a clip's generated set (deduped downstream).
    hashtag_sets: list[str] = Field(default_factory=list)
    # Extra keyword tags merged into YouTube tags.
    keyword_tags: list[str] = Field(default_factory=list)

    def prompt_block(self) -> str:
        """Render a compact persona/tone block for an LLM system prompt."""
        lines: list[str] = []
        if self.persona:
            lines.append(f"Channel persona: {self.persona}")
        if self.tone:
            lines.append(f"Voice / tone: {self.tone}")
        if self.title_style:
            lines.append(f"Title style: {self.title_style}")
        if self.cta:
            lines.append(f"Call to action to weave in when natural: {self.cta}")
        return "\n".join(lines)


class LookAndSound(BaseModel):
    """The visual / audio identity layer."""

    caption_preset: str = "bold_outline"
    lut_name: str | None = None
    transition_pack: str | None = None
    sfx_pack: str | None = None
    intro: str | None = None
    outro: str | None = None
    # If True, the automatic ffmpeg clip path will try to apply transition_pack
    # + sfx_pack between segments (when packs are available).
    auto_transitions: bool = False


class ChannelTemplate(BaseModel):
    """A complete niche template for a creator/channel.

    Backward compatible with the older GUI ``Preset`` dict: any preset can be
    upgraded into a template, and a template can be flattened back to the legacy
    settings the splitter expects.
    """

    # ---- Identity ----------------------------------------------------------
    name: str
    niche: str = "general"
    icon: str = "🎬"
    description: str = ""
    content_type: ContentType = "clips"
    builtin: bool = False

    # ---- Pacing ------------------------------------------------------------
    clip_duration: float = 30.0
    min_duration: float = 8.0
    max_duration: float = 60.0
    scene_detection: bool = False
    max_clips: int = 10

    # ---- Patterns (scorer) -------------------------------------------------
    hook_phrases: list[str] = Field(default_factory=list)
    hook_words: list[str] = Field(default_factory=list)
    scoring_weights: ScoringWeightsModel = Field(default_factory=ScoringWeightsModel)

    # ---- Voice (metadata) --------------------------------------------------
    voice: VoiceProfile = Field(default_factory=VoiceProfile)

    # ---- Look & sound ------------------------------------------------------
    look: LookAndSound = Field(default_factory=LookAndSound)

    # ---- Targets -----------------------------------------------------------
    platforms: list[Platform] = Field(default_factory=lambda: ["youtube_shorts"])
    naming_pattern: str = "{name}_clip_{num:03d}"
    add_captions: bool = True
    quality: str = "youtube_hd"

    # ---- Metadata ----------------------------------------------------------
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # ---- Conversions -------------------------------------------------------

    @property
    def slug(self) -> str:
        return self.name.replace(" ", "_").lower()

    @classmethod
    def from_preset_dict(cls, data: dict) -> "ChannelTemplate":
        """Upgrade a legacy GUI ``Preset`` dict into a template (best-effort)."""
        look = LookAndSound(
            caption_preset="bold_outline",
            lut_name=data.get("lut_name"),
        )
        return cls(
            name=data.get("name", "Imported Preset"),
            niche=data.get("category", "general"),
            description=data.get("description", ""),
            clip_duration=float(data.get("clip_duration", 30)),
            min_duration=float(data.get("min_scene_duration", 8) or 8),
            scene_detection=bool(data.get("scene_detection", False)),
            max_clips=int(data.get("max_clips", 10)),
            platforms=list(data.get("platforms", ["youtube_shorts"])) or ["youtube_shorts"],
            naming_pattern=data.get("naming_pattern", "{name}_clip_{num:03d}"),
            add_captions=bool(data.get("add_captions", True)),
            quality=data.get("quality", "youtube_hd"),
            look=look,
        )

    def touch(self) -> None:
        self.modified_at = datetime.now().isoformat()
