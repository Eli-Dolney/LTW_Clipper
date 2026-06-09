#!/usr/bin/env python3
"""Vertical video conversion (landscape -> 9:16) for Shorts / TikTok / Reels.

By default uses smart subject-tracked cropping from :mod:`src.core.reframe`.
Pass ``--mode=center`` to use the old behavior (center crop, no tracking).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .reframe.renderer import ReframeRenderer, RenderConfig
from .reframe.tracker import TrackerConfig

log = logging.getLogger(__name__)


def crop_to_vertical(
    video_path: str | Path,
    output_path: str | Path | None = None,
    *,
    mode: str = "smart",
    layout: str = "crop",
    smoothing: float = 0.35,
    deadzone: float = 0.04,
    headroom: float = 0.08,
    zoom: float = 1.0,
) -> bool:
    """Convert a video to 9:16.

    Parameters
    ----------
    video_path:
        Source video file.
    output_path:
        Destination. Defaults to ``<stem>_vertical.mp4`` next to the source.
    mode:
        ``"smart"`` (MediaPipe face tracking, default) or ``"center"`` (old
        behavior, no tracking).
    """
    src = Path(video_path)
    if not src.exists():
        print(f"❌ Not found: {src}")
        return False

    dst = Path(output_path) if output_path else src.parent / f"{src.stem}_vertical.mp4"
    dst.parent.mkdir(parents=True, exist_ok=True)

    print(f"📱 Converting to vertical ({mode}, {layout}): {src.name}")

    renderer = ReframeRenderer(
        tracker_config=TrackerConfig(
            smoothing=smoothing, deadzone=deadzone, headroom=headroom, zoom=zoom,
        ),
        render_config=RenderConfig(layout=layout),  # type: ignore[arg-type]
    )
    try:
        if mode == "center":
            renderer.render_center(src, dst)
        else:
            renderer.render(src, dst)
        print(f"   ✅ Saved to: {dst.name}")
        return True
    except Exception as exc:  # noqa: BLE001
        log.exception("Vertical render failed")
        print(f"   ❌ Error converting {src.name}: {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert videos to vertical 9:16 format")
    parser.add_argument("--file", help="Specific video file to convert")
    parser.add_argument("--dir", help="Directory of videos to convert")
    parser.add_argument(
        "--mode",
        choices=["smart", "center"],
        default="smart",
        help="Cropping mode: 'smart' tracks faces, 'center' is the old center crop.",
    )
    parser.add_argument(
        "--layout",
        choices=["crop", "fit", "blur"],
        default="crop",
        help="Reframe layout: crop (tracked fill), fit (letterbox), blur (blurred bg).",
    )
    parser.add_argument("--smoothing", type=float, default=0.35, help="EMA smoothing 0..1")
    parser.add_argument("--deadzone", type=float, default=0.04, help="Deadzone fraction")
    parser.add_argument("--headroom", type=float, default=0.08, help="Headroom bias")
    parser.add_argument("--zoom", type=float, default=1.0, help="Crop zoom factor")
    args = parser.parse_args()

    if args.file:
        crop_to_vertical(
            args.file, mode=args.mode, layout=args.layout,
            smoothing=args.smoothing, deadzone=args.deadzone,
            headroom=args.headroom, zoom=args.zoom,
        )
    elif args.dir:
        folder = Path(args.dir)
        videos = [
            v for v in folder.glob("*.mp4")
            if "_vertical" not in v.name
        ]
        print(f"Found {len(videos)} videos in {folder}")
        for vid in videos:
            crop_to_vertical(
                vid, mode=args.mode, layout=args.layout,
                smoothing=args.smoothing, deadzone=args.deadzone,
                headroom=args.headroom, zoom=args.zoom,
            )
    else:
        print("Please provide --file or --dir")


if __name__ == "__main__":
    main()
