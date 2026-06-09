"""Shared pydantic v2 data models used across the LTW pipeline.

These are the *stable contract* between stages: transcribe -> analyze -> score
-> plan -> reframe -> caption -> render -> package. Any stage can be rerun
independently as long as it emits / consumes these shapes.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ---- Transcription ----------------------------------------------------------

class WordTiming(BaseModel):
    """A single word with start/end timestamps in seconds."""

    word: str
    start: float
    end: float
    probability: float = 1.0


class TranscriptSegment(BaseModel):
    """Sentence-like segment produced by Whisper."""

    id: int
    start: float
    end: float
    text: str
    words: list[WordTiming] = Field(default_factory=list)

    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class Transcript(BaseModel):
    """Full transcription result for a single source video."""

    language: str = ""
    duration: float = 0.0
    segments: list[TranscriptSegment] = Field(default_factory=list)

    def text(self) -> str:
        return " ".join(seg.text.strip() for seg in self.segments).strip()

    def words(self) -> list[WordTiming]:
        out: list[WordTiming] = []
        for seg in self.segments:
            out.extend(seg.words)
        return out


# ---- Visual / audio feature timeline ---------------------------------------

class VisualFrameFeature(BaseModel):
    """Cheap per-sample visual stats used by the heuristic scorer."""

    timestamp: float
    motion: float = 0.0
    face_count: int = 0
    vibrancy: float = 0.0
    brightness: float = 0.0


class AudioWindow(BaseModel):
    """Short audio window stats (RMS energy, etc.)."""

    start: float
    end: float
    rms: float = 0.0
    peak: float = 0.0


class MediaFeatures(BaseModel):
    """Collected time-series features for a source video."""

    visual: list[VisualFrameFeature] = Field(default_factory=list)
    audio: list[AudioWindow] = Field(default_factory=list)


# ---- Clip plan --------------------------------------------------------------

Platform = Literal["youtube", "youtube_shorts", "tiktok", "instagram_reels"]


class ClipSuggestion(BaseModel):
    """One proposed clip produced by the highlight engine.

    Times are seconds within the source video.
    """

    start: float
    end: float
    title: str = ""
    hook: str = ""
    caption: str = ""
    tags: list[str] = Field(default_factory=list)
    platform_fit: list[Platform] = Field(default_factory=lambda: ["youtube_shorts"])
    virality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str = ""
    source_segment_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_times(self) -> "ClipSuggestion":
        if self.end <= self.start:
            raise ValueError(f"end ({self.end}) must be greater than start ({self.start})")
        return self

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class ClipPlan(BaseModel):
    """Ordered list of clip suggestions for a source video."""

    source_video: Path
    created_at: datetime = Field(default_factory=datetime.now)
    clips: list[ClipSuggestion] = Field(default_factory=list)
    generator: str = "heuristic"  # "heuristic" | "heuristic+ollama"
    notes: str = ""


# ---- Clip-level metadata (published output) --------------------------------

class YouTubeMetadata(BaseModel):
    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    chapters: list[tuple[float, str]] = Field(default_factory=list)


class ShortsMetadata(BaseModel):
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    platforms: list[Platform] = Field(default_factory=lambda: ["youtube_shorts"])


class ClipMetadata(BaseModel):
    """All the publishable metadata we produce for a single rendered clip."""

    slug: str
    start: float
    end: float
    virality_score: float = 0.0
    rationale: str = ""
    thumbnail_text: str = ""
    youtube: YouTubeMetadata = Field(default_factory=YouTubeMetadata)
    shorts: ShortsMetadata = Field(default_factory=ShortsMetadata)


# ---- Job context ------------------------------------------------------------

class JobContext(BaseModel):
    """The single mutable record that flows through every pipeline stage.

    Paths are the source of truth for artifacts on disk; in-memory fields
    (transcript, features, plan) are convenience caches populated as stages
    run. A job can always be resumed from paths alone.
    """

    source_video: Path
    output_root: Path
    project_name: str = ""
    run_id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))

    transcript: Transcript | None = None
    features: MediaFeatures | None = None
    plan: ClipPlan | None = None

    # Populated as clips are rendered.
    rendered_clip_dirs: list[Path] = Field(default_factory=list)

    @property
    def project_dir(self) -> Path:
        name = self.project_name or self.source_video.stem
        return self.output_root / name

    @property
    def clips_dir(self) -> Path:
        return self.project_dir / "clips"

    @property
    def logs_dir(self) -> Path:
        return self.project_dir / "logs"

    @property
    def transcript_path(self) -> Path:
        return self.project_dir / "transcript.json"

    @property
    def plan_path(self) -> Path:
        return self.project_dir / "plan.json"

    def ensure_dirs(self) -> None:
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
