"""Resolve ffmpeg/ffprobe binaries (bundled app or PATH)."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def bundled_ffmpeg_dir() -> Path:
    """Directory where PyInstaller or first-run setup places ffmpeg."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return base / "ffmpeg"
    return repo_root() / "vendor" / "ffmpeg"


def resolve_ffmpeg(binary: str = "ffmpeg") -> str:
    """Return path to ffmpeg binary.

    Order: ``LTW_FFMPEG`` env -> bundled vendor -> PATH.
    """
    override = os.environ.get("LTW_FFMPEG")
    if override:
        p = Path(override)
        return str(p if p.is_file() else p / binary)

    system = platform.system().lower()
    bundle = bundled_ffmpeg_dir()
    candidates = [
        bundle / system / binary,
        bundle / binary,
    ]
    for cand in candidates:
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand)

    found = shutil.which(binary)
    if found:
        return found
    return binary


def resolve_ffprobe() -> str:
    ff = resolve_ffmpeg("ffmpeg")
    if ff.endswith("ffmpeg"):
        probe = ff.replace("ffmpeg", "ffprobe")
        if Path(probe).is_file():
            return probe
    return shutil.which("ffprobe") or "ffprobe"
