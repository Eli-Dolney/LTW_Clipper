"""Layer dialog, music, and SFX with ducking — pure ffmpeg filtergraphs."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..render.ffmpeg import FFmpegRunner, probe_media
from ..render.ffmpeg_paths import resolve_ffmpeg

log = logging.getLogger(__name__)


@dataclass
class AudioMixOptions:
    """Controls for layered audio on a video."""

    dialog_volume: float = 1.0
    music_volume: float = 0.35
    duck_music: bool = True
    duck_threshold: float = 0.02
    duck_ratio: float = 8.0
    duck_attack_ms: int = 50
    duck_release_ms: int = 400
    announcer_volume: float = 1.2
    sfx_volume: float = 0.9
    crf: int = 20
    preset: str = "medium"


def build_audio_mix_filtergraph(
    *,
    duration: float,
    has_dialog: bool = True,
    has_music: bool = True,
    has_announcer: bool = False,
    has_sfx_hits: bool = False,
    sfx_hit_count: int = 0,
    options: AudioMixOptions | None = None,
) -> tuple[str, str]:
    """Build filter_complex for video + layered audio.

    Input layout:
    - ``[0]`` video with optional dialog audio
    - ``[1]`` music bed (looped/trimmed to duration)
    - ``[2]`` announcer clip (optional, plays from start)
    - ``[3]`` SFX one-shot (optional, split+delayed for each hit)

    Returns ``(filter_complex, audio_label)``.
    """
    opts = options or AudioMixOptions()
    chains: list[str] = []
    mix_inputs: list[str] = []

    dialog_label = "dialog"
    if has_dialog:
        chains.append(f"[0:a]volume={opts.dialog_volume}[dialog]")

    if has_music:
        dur = max(0.1, duration)
        chains.append(
            f"[1:a]volume={opts.music_volume},aloop=loop=-1:size=2e+09,"
            f"atrim=0:{dur:.3f},asetpts=PTS-STARTPTS[music_raw]"
        )
        if has_dialog and opts.duck_music:
            chains.append(
                f"[music_raw][{dialog_label}]sidechaincompress="
                f"threshold={opts.duck_threshold}:ratio={opts.duck_ratio}:"
                f"attack={opts.duck_attack_ms}:release={opts.duck_release_ms}[music]"
            )
        else:
            chains.append("[music_raw]anull[music]")
        mix_inputs.append("[music]")

    if has_dialog:
        mix_inputs.insert(0, f"[{dialog_label}]")
    elif not mix_inputs and has_music:
        pass  # music-only handled below

    if has_announcer:
        chains.append(f"[2:a]volume={opts.announcer_volume}[ann]")
        mix_inputs.append("[ann]")

    if has_sfx_hits and sfx_hit_count > 0:
        splits = "".join(f"[sh{k}]" for k in range(sfx_hit_count))
        chains.append(f"[3:a]asplit={sfx_hit_count}{splits}")
        for k in range(sfx_hit_count):
            chains.append(f"[sh{k}]volume={opts.sfx_volume}[sfx{k}]")
            mix_inputs.append(f"[sfx{k}]")

    if not mix_inputs:
        raise ValueError("need at least one audio source")

    if len(mix_inputs) == 1:
        src = mix_inputs[0].strip("[]")
        chains.append(f"[{src}]anull[aout]")
    else:
        chains.append(
            "".join(mix_inputs)
            + f"amix=inputs={len(mix_inputs)}:duration=first:normalize=0[aout]"
        )

    return ";".join(chains), "aout"


class AudioMixer:
    """Burn layered audio onto a video via ffmpeg."""

    def __init__(self, runner: FFmpegRunner | None = None) -> None:
        self.runner = runner or FFmpegRunner()
        self.ffmpeg = self.runner.ffmpeg or resolve_ffmpeg()

    def mix(
        self,
        video: Path,
        output: Path,
        *,
        music: Path | None = None,
        announcer: Path | None = None,
        sfx: Path | None = None,
        sfx_hit_times: list[float] | None = None,
        options: AudioMixOptions | None = None,
    ) -> Path:
        opts = options or AudioMixOptions()
        probe = probe_media(video)
        duration = probe.duration
        if duration <= 0:
            raise ValueError(f"Could not determine duration of {video}")

        has_dialog = probe.has_audio
        has_music = music is not None and music.is_file()
        has_announcer = announcer is not None and announcer.is_file()
        hit_times = sfx_hit_times or []
        has_sfx = sfx is not None and sfx.is_file() and hit_times

        # Build graph without SFX delays first (sfx handled via adelay in extended version)
        filter_complex, alabel = build_audio_mix_filtergraph(
            duration=duration,
            has_dialog=has_dialog,
            has_music=has_music,
            has_announcer=has_announcer,
            has_sfx_hits=bool(has_sfx),
            sfx_hit_count=len(hit_times) if has_sfx else 0,
            options=opts,
        )

        # Inject adelay for SFX hits
        if has_sfx and hit_times:
            chains = filter_complex.split(";")
            new_chains: list[str] = []
            sfx_idx = 0
            for chain in chains:
                if chain.startswith("[sh") and "volume=" in chain and "[sfx" in chain:
                    ms = max(0, int(hit_times[sfx_idx] * 1000))
                    label = f"sfx{sfx_idx}"
                    new_chains.append(
                        f"[sh{sfx_idx}]adelay={ms}|{ms},volume={opts.sfx_volume}[{label}]"
                    )
                    sfx_idx += 1
                else:
                    new_chains.append(chain)
            filter_complex = ";".join(new_chains)

        cmd = [self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(video)]
        if has_music:
            cmd += ["-i", str(music)]
        if has_announcer:
            cmd += ["-i", str(announcer)]
        if has_sfx:
            cmd += ["-i", str(sfx)]

        cmd += [
            "-filter_complex", filter_complex,
            "-map", "0:v", "-map", f"[{alabel}]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            "-shortest",
            str(output),
        ]

        output.parent.mkdir(parents=True, exist_ok=True)
        log.info("Mixing audio: %s -> %s", video.name, output.name)
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            raise RuntimeError(f"Audio mix failed: {stderr[:500]}") from exc
        return output
