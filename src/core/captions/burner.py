"""Burn ASS captions into a video using ffmpeg."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


class CaptionBurner:
    """Run ffmpeg with ``-vf ass=...`` to produce a subtitled copy."""

    def __init__(self, ffmpeg_binary: str = "ffmpeg") -> None:
        self.ffmpeg = ffmpeg_binary

    def burn(
        self,
        source: Path,
        ass_path: Path,
        output: Path,
        *,
        crf: int = 20,
        preset: str = "medium",
    ) -> Path:
        if not source.exists():
            raise FileNotFoundError(source)
        if not ass_path.exists():
            raise FileNotFoundError(ass_path)

        output.parent.mkdir(parents=True, exist_ok=True)
        # ffmpeg ass filter needs escaped path (esp. on Windows / spaces).
        ass_escaped = _escape_ffmpeg_path(ass_path)

        cmd = [
            self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(source),
            "-vf", f"ass={ass_escaped}",
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(output),
        ]
        log.info("Burning captions: %s + %s -> %s", source.name, ass_path.name, output.name)
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            # If audio copy fails (e.g. unsupported), retry with re-encode.
            if "Could not find tag" in stderr or "Invalid data" in stderr:
                retry = cmd[:-4] + ["-c:a", "aac", "-b:a", "160k", str(output)]
                subprocess.run(retry, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                raise RuntimeError(f"Caption burn failed: {stderr[:500]}") from exc
        return output


def _escape_ffmpeg_path(path: Path) -> str:
    """Escape a path for use inside an ffmpeg filtergraph argument."""
    s = str(path)
    # ffmpeg filter parser treats `:` and `\` specially; wrap in single quotes
    # and escape existing single quotes.
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", r"\'")
