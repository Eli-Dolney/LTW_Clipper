#!/usr/bin/env python3
"""First-run setup: copy settings, download Whisper model, optional ffmpeg hint."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print("LTW Video Splitter Pro — First-run setup")
    print("=" * 40)

    cfg = ROOT / "config" / "settings.yaml"
    example = ROOT / "config" / "settings.example.yaml"
    if not cfg.is_file() and example.is_file():
        shutil.copy(example, cfg)
        print(f"Created {cfg}")

    if not shutil.which("ffmpeg"):
        print("\nffmpeg not found on PATH.")
        print("  macOS: brew install ffmpeg")
        print("  Or place binaries in vendor/ffmpeg/darwin/")
    else:
        print(f"ffmpeg: {shutil.which('ffmpeg')}")

    try:
        from faster_whisper import WhisperModel

        print("\nDownloading Whisper 'small' model (one-time, ~500MB)...")
        WhisperModel("small", device="cpu", compute_type="int8",
                     download_root=str(Path.home() / ".cache" / "ltw" / "whisper"))
        print("Whisper model ready.")
    except ImportError:
        print("\nInstall deps first: pip install -r requirements.txt")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Whisper download failed: {exc}")
        return 1

    print("\nOptional: install Ollama for smarter titles")
    print("  https://ollama.com")
    print("  ollama pull llama3.1:8b")
    print("\nDone. Launch with: python launch_gui.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
