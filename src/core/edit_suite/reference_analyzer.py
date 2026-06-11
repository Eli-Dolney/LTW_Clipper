"""Analyze a reference edit and extract a replicable style recipe."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

from ..render.ffmpeg import probe_media
from ..render.ffmpeg_paths import resolve_ffmpeg
from .models import BeatMap, EditStyleRecipe, ReferenceAnalysis

log = logging.getLogger(__name__)


def compute_cut_stats(cut_timestamps: list[float], duration: float) -> dict:
    """Pure stats from cut timestamps (testable without ffmpeg)."""
    if not cut_timestamps or duration <= 0:
        return {
            "cut_count": 0,
            "cuts_per_minute": 0.0,
            "avg_shot_length": duration,
            "min_shot_length": duration,
            "max_shot_length": duration,
        }
    points = [0.0] + sorted(cut_timestamps) + [duration]
    lengths = [points[i + 1] - points[i] for i in range(len(points) - 1) if points[i + 1] > points[i]]
    if not lengths:
        lengths = [duration]
    minutes = max(duration / 60.0, 0.01)
    return {
        "cut_count": len(cut_timestamps),
        "cuts_per_minute": len(cut_timestamps) / minutes,
        "avg_shot_length": sum(lengths) / len(lengths),
        "min_shot_length": min(lengths),
        "max_shot_length": max(lengths),
    }


def detect_scene_cuts(video: Path, *, threshold: float = 0.35) -> list[float]:
    """Detect scene-change timestamps via ffmpeg ``select=gt(scene)``."""
    ffmpeg = resolve_ffmpeg()
    cmd = [
        ffmpeg, "-hide_banner", "-i", str(video),
        "-filter:v", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = proc.stderr + proc.stdout
    cuts: list[float] = []
    for line in output.splitlines():
        if "pts_time:" in line:
            match = re.search(r"pts_time:([0-9.]+)", line)
            if match:
                cuts.append(float(match.group(1)))
    return cuts


def detect_audio_peaks(
    video: Path,
    *,
    peak_threshold: float = 0.65,
    min_gap: float = 0.4,
) -> list[float]:
    """Find loud audio peaks (announcer hits, impacts) via astats."""
    ffmpeg = resolve_ffmpeg()
    cmd = [
        ffmpeg, "-hide_banner", "-i", str(video),
        "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    peaks: list[float] = []
    last_peak = -999.0
    current_time = 0.0
    for line in proc.stderr.splitlines():
        if "pts_time:" in line:
            match = re.search(r"pts_time:([0-9.]+)", line)
            if match:
                current_time = float(match.group(1))
        if "RMS_level=" in line:
            match = re.search(r"RMS_level=(-?[0-9.]+)", line)
            if not match:
                continue
            rms_db = float(match.group(1))
            # Normalize dB to 0-1-ish scale (-60 silent, 0 loud)
            level = max(0.0, min(1.0, (rms_db + 60.0) / 60.0))
            if level >= peak_threshold and current_time - last_peak >= min_gap:
                peaks.append(round(current_time, 3))
                last_peak = current_time
    return peaks


def infer_style_tag(stats: dict, peak_density: float) -> str:
    """Guess sports vs cinematic from cut rate."""
    cpm = stats.get("cuts_per_minute", 0.0)
    avg = stats.get("avg_shot_length", 3.0)
    if cpm >= 22 or avg <= 2.0:
        return "sports"
    if cpm >= 14 or peak_density >= 8:
        return "hype"
    if avg >= 3.0:
        return "cinematic"
    return "custom"


class ReferenceAnalyzer:
    """Analyze a reference sports/movie edit and produce a style recipe."""

    def analyze(
        self,
        video: Path,
        *,
        scene_threshold: float = 0.35,
        beat_map: BeatMap | None = None,
    ) -> ReferenceAnalysis:
        video = Path(video)
        probe = probe_media(video)
        cuts = detect_scene_cuts(video, threshold=scene_threshold)
        peaks = detect_audio_peaks(video)
        stats = compute_cut_stats(cuts, probe.duration)
        minutes = max(probe.duration / 60.0, 0.01)
        peak_density = len(peaks) / minutes

        tag = infer_style_tag(stats, peak_density)
        if tag == "sports":
            base = EditStyleRecipe.sports_default()
        elif tag == "cinematic":
            base = EditStyleRecipe.cinematic_default()
        else:
            base = EditStyleRecipe(style_tag=tag)

        transition = "fade" if stats["avg_shot_length"] < 2.5 else "dissolve"
        transition_dur = 0.25 if stats["avg_shot_length"] < 2.0 else 0.5

        recipe = EditStyleRecipe(
            source=str(video),
            duration=probe.duration,
            cut_count=stats["cut_count"],
            cuts_per_minute=round(stats["cuts_per_minute"], 1),
            avg_shot_length=round(stats["avg_shot_length"], 2),
            min_shot_length=round(stats["min_shot_length"], 2),
            max_shot_length=round(stats["max_shot_length"], 2),
            transition=transition,
            transition_dur=transition_dur,
            sfx_density=round(peak_density, 1),
            music_volume=base.music_volume,
            music_duck_db=base.music_duck_db,
            beats_per_clip=2 if tag == "sports" else 4,
            style_tag=tag,
        )

        if beat_map and beat_map.tempo > 0:
            recipe.beats_per_clip = max(1, int(round(60.0 / beat_map.tempo * stats["avg_shot_length"])))

        return ReferenceAnalysis(
            recipe=recipe,
            cut_timestamps=cuts,
            audio_peak_timestamps=peaks,
        )

    def save(self, analysis: ReferenceAnalysis, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(analysis.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, path: Path) -> ReferenceAnalysis:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return ReferenceAnalysis.model_validate(data)
