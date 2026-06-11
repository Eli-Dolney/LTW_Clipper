"""Automatic transitions + SFX for the local clip path (ffmpeg only).

Joins multiple clips into a single montage using ffmpeg ``xfade`` (video) and
``acrossfade`` (audio), and optionally mixes a transition sound effect at each
cut. This is the fully-automatic, no-Resolve route — great for building a
short-form compilation from several highlight clips.

The filtergraph construction is pure and unit-tested; the ffmpeg invocation is a
thin wrapper kept out of the test path (consistent with the rest of the render
layer, which never shells out during tests).
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg import FFmpegRunner, probe_media
from .ffmpeg_paths import resolve_ffmpeg

log = logging.getLogger(__name__)


# Friendly name -> ffmpeg xfade transition name.
TRANSITIONS: dict[str, str] = {
    "fade": "fade",
    "fade_black": "fadeblack",
    "fade_white": "fadewhite",
    "dissolve": "dissolve",
    "wipe_left": "wipeleft",
    "wipe_right": "wiperight",
    "wipe_up": "wipeup",
    "wipe_down": "wipedown",
    "slide_left": "slideleft",
    "slide_right": "slideright",
    "circle": "circlecrop",
    "radial": "radial",
    "pixelize": "pixelize",
    "smooth_left": "smoothleft",
}


def resolve_transition(name: str) -> str:
    """Map a friendly transition name to an ffmpeg xfade name (default 'fade')."""
    return TRANSITIONS.get(name, name if name in TRANSITIONS.values() else "fade")


def compute_offsets(durations: list[float], transition_dur: float) -> list[float]:
    """Offsets (seconds) for each xfade when chaining clips left-to-right.

    For clip k (k>=1) added to the running montage, the xfade ``offset`` is the
    visible length of everything before it minus one transition (so the next
    clip starts fading in ``transition_dur`` before the previous one ends).
    """
    offsets: list[float] = []
    cumulative = 0.0
    for k in range(1, len(durations)):
        cumulative += durations[k - 1]
        offsets.append(round(cumulative - k * transition_dur, 3))
    return offsets


def build_filtergraph(
    durations: list[float],
    *,
    transition: str = "fade",
    transition_dur: float = 0.5,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    with_audio: bool = True,
    sfx: bool = False,
) -> tuple[str, str, str | None]:
    """Build an ffmpeg ``-filter_complex`` graph for an N-clip montage.

    Returns ``(filter_complex, video_label, audio_label)``. ``audio_label`` is
    ``None`` when ``with_audio`` is False. Inputs are assumed to be ``[0..n-1]``
    video clips; when ``sfx`` is True an extra input ``[n]`` is the SFX file.
    """
    n = len(durations)
    if n == 0:
        raise ValueError("need at least one clip")

    xname = resolve_transition(transition)
    chains: list[str] = []

    # Normalize every clip to a common size/fps/SAR so xfade can chain them.
    norm_labels: list[str] = []
    for i in range(n):
        lbl = f"v{i}n"
        chains.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[{lbl}]"
        )
        norm_labels.append(lbl)

    # Video xfade chain.
    if n == 1:
        video_label = norm_labels[0]
    else:
        offsets = compute_offsets(durations, transition_dur)
        prev = norm_labels[0]
        for k in range(1, n):
            out = f"vx{k}" if k < n - 1 else "vout"
            chains.append(
                f"[{prev}][{norm_labels[k]}]xfade=transition={xname}:"
                f"duration={transition_dur}:offset={offsets[k - 1]}[{out}]"
            )
            prev = out
        video_label = "vout"

    audio_label: str | None = None
    if with_audio:
        if n == 1:
            # Route through filter graph so -map uses [label], not invalid [0:a].
            chains.append("[0:a]anull[abase]")
            audio_label = "abase"
        else:
            prev_a = "0:a"
            for k in range(1, n):
                out = f"ax{k}" if k < n - 1 else "abase"
                chains.append(
                    f"[{prev_a}][{k}:a]acrossfade=d={transition_dur}:c1=tri:c2=tri[{out}]"
                )
                prev_a = out
            audio_label = "abase"

        if sfx and n > 1:
            # One SFX input ([n]) split and delayed to each cut, mixed with base.
            offsets = compute_offsets(durations, transition_dur)
            splits = "".join(f"[s{k}]" for k in range(len(offsets)))
            chains.append(f"[{n}:a]asplit={len(offsets)}{splits}")
            mix_inputs = [f"[{audio_label}]"]
            for k, off in enumerate(offsets):
                ms = max(0, int(off * 1000))
                chains.append(f"[s{k}]adelay={ms}|{ms}[sd{k}]")
                mix_inputs.append(f"[sd{k}]")
            chains.append(
                "".join(mix_inputs)
                + f"amix=inputs={len(mix_inputs)}:duration=first:normalize=0[aout]"
            )
            audio_label = "aout"

    return ";".join(chains), video_label, audio_label


@dataclass
class TransitionOptions:
    transition: str = "fade"
    transition_dur: float = 0.5
    width: int = 1080
    height: int = 1920
    fps: int = 30
    crf: int = 20
    preset: str = "medium"


class TransitionComposer:
    """Render a montage of clips with transitions (+ optional SFX) via ffmpeg."""

    def __init__(self, runner: FFmpegRunner | None = None) -> None:
        self.runner = runner or FFmpegRunner()
        self.ffmpeg = self.runner.ffmpeg or resolve_ffmpeg()

    def compose(
        self,
        clips: list[Path],
        output: Path,
        *,
        options: TransitionOptions | None = None,
        sfx: Path | None = None,
    ) -> Path:
        opts = options or TransitionOptions()
        if not clips:
            raise ValueError("no clips to compose")
        output.parent.mkdir(parents=True, exist_ok=True)

        durations: list[float] = []
        with_audio = True
        for c in clips:
            probe = probe_media(c)
            durations.append(probe.duration)
            with_audio = with_audio and probe.has_audio

        use_sfx = sfx is not None and sfx.exists() and with_audio
        filter_complex, vlabel, alabel = build_filtergraph(
            durations,
            transition=opts.transition,
            transition_dur=opts.transition_dur,
            width=opts.width,
            height=opts.height,
            fps=opts.fps,
            with_audio=with_audio,
            sfx=use_sfx,
        )

        def build_cmd(encoder: str) -> list[str]:
            cmd = [self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
            for c in clips:
                cmd += ["-i", str(c)]
            if use_sfx:
                cmd += ["-i", str(sfx)]
            cmd += ["-filter_complex", filter_complex, "-map", f"[{vlabel}]"]
            if alabel is not None:
                cmd += ["-map", f"[{alabel}]"]
            cmd += ["-c:v", encoder, "-pix_fmt", "yuv420p", "-preset", opts.preset,
                    "-crf", str(opts.crf)]
            if alabel is not None:
                cmd += ["-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2"]
            cmd.append(str(output))
            return cmd

        encoder = self.runner.video_encoder
        try:
            subprocess.run(build_cmd(encoder), check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            # Hardware encoders (videotoolbox/nvenc/qsv) can be unavailable or busy;
            # fall back to software libx264 once before giving up.
            if encoder != "libx264":
                log.warning("Encoder %s failed (%s), retrying with libx264",
                            encoder, stderr[:160])
                try:
                    subprocess.run(build_cmd("libx264"), check=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    return output
                except subprocess.CalledProcessError as exc2:
                    stderr = exc2.stderr.decode("utf-8", errors="replace") if exc2.stderr else ""
            raise RuntimeError(f"ffmpeg montage failed: {stderr[:500]}") from exc
        return output


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compose a montage from clips with transitions + optional SFX (local, ffmpeg)."
    )
    parser.add_argument("clips", nargs="+", help="Input clip files in order")
    parser.add_argument("-o", "--output", required=True, help="Output montage path")
    parser.add_argument("-t", "--transition", default="fade",
                        help=f"Transition: {', '.join(TRANSITIONS)}")
    parser.add_argument("-d", "--duration", type=float, default=0.5, help="Transition seconds")
    parser.add_argument("--sfx", default=None, help="Optional transition SFX audio file")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    composer = TransitionComposer()
    out = composer.compose(
        [Path(c) for c in args.clips],
        Path(args.output),
        options=TransitionOptions(
            transition=args.transition, transition_dur=args.duration,
            width=args.width, height=args.height, fps=args.fps,
        ),
        sfx=Path(args.sfx) if args.sfx else None,
    )
    print(f"✅ Montage written: {out}")


if __name__ == "__main__":
    _main()
