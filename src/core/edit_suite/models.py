"""Data models for the Edit Suite."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BeatMap(BaseModel):
    """Beat timestamps from music analysis."""

    source: str = ""
    tempo: float = 0.0
    total_beats: int = 0
    beats: list[float] = Field(default_factory=list)

    def intervals(self) -> list[tuple[float, float]]:
        """Return (start, end) pairs between consecutive beats."""
        if len(self.beats) < 2:
            return []
        return [
            (self.beats[i], self.beats[i + 1])
            for i in range(len(self.beats) - 1)
        ]

    def segment_duration(self, beats_per_segment: int = 2) -> float:
        """Average seconds covered by N beat intervals."""
        ivs = self.intervals()
        if not ivs:
            return 1.0
        take = min(beats_per_segment, len(ivs))
        return sum(end - start for start, end in ivs[:take]) / take


class EditStyleRecipe(BaseModel):
    """Replicated style from a reference edit — apply to your own clips."""

    source: str = ""
    duration: float = 0.0
    cut_count: int = 0
    cuts_per_minute: float = 0.0
    avg_shot_length: float = 0.0
    min_shot_length: float = 0.0
    max_shot_length: float = 0.0
    transition: str = "fade"
    transition_dur: float = 0.3
    sfx_density: float = 0.0  # peaks per minute
    music_duck_db: float = -12.0
    music_volume: float = 0.35
    dialog_volume: float = 1.0
    beats_per_clip: int = 2
    style_tag: str = "sports"  # sports | cinematic | hype | custom

    @classmethod
    def sports_default(cls) -> "EditStyleRecipe":
        return cls(
            transition="fade",
            transition_dur=0.25,
            avg_shot_length=1.5,
            cuts_per_minute=28.0,
            music_volume=0.4,
            music_duck_db=-10.0,
            beats_per_clip=2,
            style_tag="sports",
        )

    @classmethod
    def cinematic_default(cls) -> "EditStyleRecipe":
        return cls(
            transition="dissolve",
            transition_dur=0.6,
            avg_shot_length=3.5,
            cuts_per_minute=12.0,
            music_volume=0.3,
            music_duck_db=-14.0,
            beats_per_clip=4,
            style_tag="cinematic",
        )


class ReferenceAnalysis(BaseModel):
    """Full analysis output from a reference edit."""

    recipe: EditStyleRecipe
    cut_timestamps: list[float] = Field(default_factory=list)
    audio_peak_timestamps: list[float] = Field(default_factory=list)
