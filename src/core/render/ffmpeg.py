"""Centralized ffmpeg helpers: probe, encoder selection, clip extraction, thumbnails.

All functions assume ``ffmpeg`` / ``ffprobe`` are installed or pointed to
explicitly. No network calls. No cloud dependencies.
"""

from __future__ import annotations

import json
import logging
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg_paths import resolve_ffmpeg, resolve_ffprobe

log = logging.getLogger(__name__)


# ---- Probing ---------------------------------------------------------------

@dataclass
class ProbeResult:
    path: Path
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    video_codec: str = ""
    audio_codec: str = ""
    has_audio: bool = False


def ffmpeg_available(binary: str = "ffmpeg") -> bool:
    resolved = resolve_ffmpeg(binary)
    return Path(resolved).is_file() or shutil.which(resolved) is not None


def probe_media(path: Path, *, ffprobe: str | None = None) -> ProbeResult:
    if not path.exists():
        raise FileNotFoundError(path)
    ffprobe = ffprobe or resolve_ffprobe()
    if not Path(ffprobe).is_file() and not shutil.which(ffprobe):
        raise RuntimeError(f"{ffprobe} not on PATH")

    cmd = [
        ffprobe,
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    out = subprocess.run(cmd, check=True, capture_output=True)
    data = json.loads(out.stdout.decode("utf-8"))

    streams = data.get("streams", [])
    vid = next((s for s in streams if s.get("codec_type") == "video"), None)
    aud = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})

    width = int(vid.get("width", 0)) if vid else 0
    height = int(vid.get("height", 0)) if vid else 0
    fps = _parse_fps(vid.get("avg_frame_rate", "0/0")) if vid else 0.0
    duration = float(fmt.get("duration", vid.get("duration", 0.0) if vid else 0.0) or 0.0)

    return ProbeResult(
        path=path,
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        video_codec=(vid or {}).get("codec_name", ""),
        audio_codec=(aud or {}).get("codec_name", ""),
        has_audio=aud is not None,
    )


def _parse_fps(rate: str) -> float:
    try:
        if "/" in rate:
            a, b = rate.split("/", 1)
            if float(b) == 0:
                return 0.0
            return float(a) / float(b)
        return float(rate)
    except (ValueError, TypeError):
        return 0.0


# ---- Hardware acceleration -------------------------------------------------

def detect_hwaccel(force: str = "auto") -> str:
    """Return a video encoder name to use, based on OS and user override.

    ``force`` may be "auto" (default), "videotoolbox", "nvenc", "qsv",
    "vaapi", or "cpu". The returned value is an ffmpeg encoder name like
    ``h264_videotoolbox`` or ``libx264``.
    """
    if force == "cpu":
        return "libx264"

    if force != "auto":
        return _force_encoder(force)

    system = platform.system()
    if system == "Darwin":
        return "h264_videotoolbox"
    if system == "Windows":
        # We can't easily introspect NVIDIA/Intel at import time; start with
        # libx264 and let the caller override via config.
        return "libx264"
    return "libx264"  # Linux default; VAAPI requires device path, opt-in via force.


def _force_encoder(kind: str) -> str:
    mapping = {
        "videotoolbox": "h264_videotoolbox",
        "nvenc": "h264_nvenc",
        "qsv": "h264_qsv",
        "vaapi": "h264_vaapi",
    }
    return mapping.get(kind, "libx264")


# ---- Runner (clip extraction, thumbnails) ----------------------------------

class FFmpegRunner:
    """Small helper bundling ffmpeg invocations used by the pipeline."""

    def __init__(
        self,
        *,
        ffmpeg_binary: str | None = None,
        video_encoder: str | None = None,
    ) -> None:
        self.ffmpeg = ffmpeg_binary or resolve_ffmpeg()
        self.video_encoder = video_encoder or detect_hwaccel("auto") or detect_hwaccel("auto")

    # ---- Clip extraction ---------------------------------------------------

    def extract_clip(
        self,
        source: Path,
        output: Path,
        *,
        start: float,
        end: float,
        crf: int = 20,
        preset: str = "medium",
        bitrate: str | None = None,
    ) -> Path:
        """Cut ``source`` from ``start`` to ``end`` (seconds). Keeps original aspect."""
        duration = max(0.001, end - start)
        output.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{start:.3f}",
            "-t", f"{duration:.3f}",
            "-i", str(source),
            "-c:v", self.video_encoder,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "160k",
            "-ar", "44100",
            "-ac", "2",
        ]
        # libx264 cares about crf+preset; hwaccel encoders use different knobs
        # but the flags are safely ignored by most builds.
        cmd += ["-preset", preset, "-crf", str(crf)]
        if bitrate:
            cmd += ["-b:v", bitrate]
        cmd.append(str(output))

        self._run(cmd, retry_audio=True)
        return output

    # ---- Thumbnails --------------------------------------------------------

    def thumbnail(
        self,
        source: Path,
        output: Path,
        *,
        timestamp: float = 1.0,
        width: int = 1280,
    ) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{timestamp:.3f}",
            "-i", str(source),
            "-frames:v", "1",
            "-vf", f"scale={width}:-2",
            "-q:v", "2",
            str(output),
        ]
        self._run(cmd, retry_audio=False)
        return output

    # ---- Audio extraction (for ASR) ----------------------------------------

    def extract_audio_wav(self, source: Path, output: Path, *, sample_rate: int = 16000) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(source),
            "-vn",
            "-ac", "1",
            "-ar", str(sample_rate),
            "-c:a", "pcm_s16le",
            str(output),
        ]
        self._run(cmd, retry_audio=False)
        return output

    # ---- Low-level runner --------------------------------------------------

    def _run(self, cmd: list[str], *, retry_audio: bool) -> None:
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            if retry_audio and "aresample" not in " ".join(cmd):
                log.warning("ffmpeg failed, retrying with aresample filter: %s", stderr[:200])
                retry = cmd[:-1] + ["-af", "aresample=async=1:first_pts=0", cmd[-1]]
                subprocess.run(retry, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return
            raise RuntimeError(f"ffmpeg failed: {stderr[:500]}") from exc
