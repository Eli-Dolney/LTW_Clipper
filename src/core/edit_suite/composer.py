"""Orchestrate beat-sync montages and layered audio edits."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..render.ffmpeg import FFmpegRunner, probe_media
from ..render.ffmpeg_paths import resolve_ffmpeg
from ..render.transitions import TransitionComposer, TransitionOptions
from .audio_mixer import AudioMixOptions, AudioMixer
from .beats import BeatMap
from .models import EditStyleRecipe

log = logging.getLogger(__name__)


@dataclass
class EditComposeOptions:
    transition: str = "fade"
    transition_dur: float = 0.35
    width: int = 1080
    height: int = 1920
    fps: int = 30
    beats_per_clip: int = 2
    crf: int = 20
    preset: str = "medium"
    audio: AudioMixOptions | None = None


def plan_clip_durations(
    clips: list[Path],
    beat_map: BeatMap | None,
    *,
    beats_per_clip: int = 2,
    fallback_duration: float = 2.0,
) -> list[float]:
    """How long each clip should play (seconds) for a beat-synced edit."""
    if beat_map and len(beat_map.beats) > beats_per_clip:
        seg = beat_map.segment_duration(beats_per_clip)
        return [seg] * len(clips)
    return [fallback_duration] * len(clips)


class EditComposer:
    """Build sports/movie edits: montage + music + ducking + optional SFX hits."""

    def __init__(self, runner: FFmpegRunner | None = None) -> None:
        self.runner = runner or FFmpegRunner()
        self.ffmpeg = self.runner.ffmpeg or resolve_ffmpeg()
        self.montage = TransitionComposer(self.runner)
        self.mixer = AudioMixer(self.runner)

    def trim_clip(self, source: Path, output: Path, *, duration: float, start: float = 0.0) -> Path:
        """Extract a short segment from a clip."""
        output.parent.mkdir(parents=True, exist_ok=True)
        probe = probe_media(source)
        cmd = [
            self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-ss", str(start),
            "-i", str(source),
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p",
        ]
        if probe.has_audio:
            cmd += ["-c:a", "aac", "-b:a", "160k"]
        else:
            cmd += ["-an"]
        cmd.append(str(output))
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output

    def compose_montage(
        self,
        clips: list[Path],
        output: Path,
        *,
        recipe: EditStyleRecipe | None = None,
        beat_map: BeatMap | None = None,
        options: EditComposeOptions | None = None,
        sfx: Path | None = None,
    ) -> Path:
        """Trim clips to beat segments, stitch montage, optionally mix music."""
        opts = options or EditComposeOptions()
        recipe = recipe or EditStyleRecipe.sports_default()

        beats_per = recipe.beats_per_clip if recipe else opts.beats_per_clip
        durations = plan_clip_durations(clips, beat_map, beats_per_clip=beats_per)

        with tempfile.TemporaryDirectory() as tmp:
            trimmed: list[Path] = []
            tmp_dir = Path(tmp)
            for i, (clip, dur) in enumerate(zip(clips, durations)):
                out = tmp_dir / f"seg_{i:03d}.mp4"
                probe = probe_media(clip)
                start = 0.0
                if probe.duration > dur:
                    start = max(0.0, (probe.duration - dur) / 2)
                self.trim_clip(clip, out, duration=dur, start=start)
                trimmed.append(out)

            montage_path = tmp_dir / "montage.mp4"
            self.montage.compose(
                trimmed,
                montage_path,
                options=TransitionOptions(
                    transition=recipe.transition if recipe else opts.transition,
                    transition_dur=recipe.transition_dur if recipe else opts.transition_dur,
                    width=opts.width,
                    height=opts.height,
                    fps=opts.fps,
                    crf=opts.crf,
                    preset=opts.preset,
                ),
                sfx=sfx,
            )
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(montage_path, output)

        return output

    def compose_with_audio(
        self,
        clips: list[Path],
        output: Path,
        *,
        music: Path | None = None,
        announcer: Path | None = None,
        sfx: Path | None = None,
        recipe: EditStyleRecipe | None = None,
        beat_map: BeatMap | None = None,
        analysis_peaks: list[float] | None = None,
        options: EditComposeOptions | None = None,
        transition_sfx: Path | None = None,
    ) -> Path:
        """Full edit: beat-sync montage + music ducking + announcer + impact SFX."""
        opts = options or EditComposeOptions()
        recipe = recipe or EditStyleRecipe.sports_default()

        with tempfile.TemporaryDirectory() as tmp:
            montage = Path(tmp) / "montage.mp4"
            self.compose_montage(
                clips, montage,
                recipe=recipe,
                beat_map=beat_map,
                options=opts,
                sfx=transition_sfx,
            )

            needs_mix = bool(
                (music and music.is_file())
                or (announcer and announcer.is_file())
                or (sfx and sfx.is_file() and analysis_peaks)
            )
            if needs_mix:
                audio_opts = opts.audio or AudioMixOptions(
                    music_volume=recipe.music_volume,
                    dialog_volume=recipe.dialog_volume,
                )
                self.mixer.mix(
                    montage,
                    output,
                    music=music,
                    announcer=announcer,
                    sfx=sfx,
                    sfx_hit_times=analysis_peaks,
                    options=audio_opts,
                )
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(montage, output)
        return output
