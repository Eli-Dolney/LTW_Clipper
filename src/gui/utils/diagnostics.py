"""Collect diagnostics for GUI error reporting."""

from __future__ import annotations

import platform
import shutil
import sys
import traceback
from pathlib import Path


def collect_diagnostics(exc: BaseException | None = None) -> str:
    lines = [
        "LTW Video Splitter Pro — Diagnostics",
        "=" * 40,
        f"Python: {sys.version}",
        f"Platform: {platform.platform()}",
        f"Executable: {sys.executable}",
        f"ffmpeg: {shutil.which('ffmpeg') or 'NOT FOUND'}",
        f"ffprobe: {shutil.which('ffprobe') or 'NOT FOUND'}",
    ]
    try:
        from src.config import get_settings

        s = get_settings()
        lines += [
            f"Whisper model: {s.whisper.model}",
            f"HW accel: {s.ffmpeg.hwaccel}",
            f"Output root: {s.app.resolved_output_root()}",
            f"Ollama: {s.ollama.host} ({s.ollama.model})",
        ]
    except Exception as cfg_exc:  # noqa: BLE001
        lines.append(f"Settings load error: {cfg_exc}")

    if exc is not None:
        lines += ["", "Exception:", "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))]

    return "\n".join(lines)


def copy_diagnostics_to_clipboard(root, text: str) -> bool:
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
        return True
    except Exception:
        return False
