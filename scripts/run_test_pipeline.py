#!/usr/bin/env python3
"""Run Opus pipeline on the test water video with live progress."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.opus_clip_processor import OpusClipProcessor, PipelineOptions
from src.logging_setup import configure_logging


def main() -> int:
    source = ROOT / "test_videos" / (
        "Create INSANE Realistic & Interactive Water in 5 minutes in Unreal 5.5.mp4"
    )
    if not source.is_file():
        print(f"Missing: {source}")
        return 1

    output_root = ROOT / "test_videos" / "ltw_output"
    configure_logging(level="INFO")

    options = PipelineOptions(
        max_clips=3,
        whisper_model="small",
        use_ollama=False,
        burn_captions=True,
        caption_preset="bold_outline",
        force_encoder="auto",
        resume=True,
    )

    t0 = time.time()
    last_stage = ""

    def progress(stage: str, frac: float, msg: str) -> None:
        nonlocal last_stage
        if stage != last_stage:
            print(f"\n── {stage.upper()} ──")
            last_stage = stage
        print(f"  [{frac*100:5.1f}%] {msg}")

    print("LTW pipeline test run")
    print(f"Source: {source.name}")
    print(f"Output: {output_root}")
    print(f"Encoder: VideoToolbox (auto on macOS)")
    print(f"Clips: {options.max_clips}, Whisper: {options.whisper_model}")
    print()

    proc = OpusClipProcessor(options)
    ctx = proc.run(source, output_root, project_name=source.stem, progress=progress)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed/60:.1f} min")
    print(f"Project: {ctx.project_dir}")
    print(f"Rendered: {len(ctx.rendered_clip_dirs)} clip(s)")
    for d in ctx.rendered_clip_dirs:
        for f in sorted(d.glob("*")):
            if f.is_file():
                print(f"  {d.name}/{f.name} ({f.stat().st_size/1024/1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
