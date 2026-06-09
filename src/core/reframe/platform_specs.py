"""Platform aspect ratios and output resolutions for social reframing."""

from __future__ import annotations

from dataclasses import dataclass

# Map GUI platform names -> aspect + output resolution
PLATFORM_SPECS: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {
    "TikTok": ((9, 16), (1080, 1920)),
    "Instagram Reels": ((9, 16), (1080, 1920)),
    "YouTube Shorts": ((9, 16), (1080, 1920)),
    "Twitter": ((1, 1), (1080, 1080)),
    "LinkedIn": ((16, 9), (1920, 1080)),
}

# Canonical aspect -> resolution (dedupe when multiple platforms share aspect)
ASPECT_RESOLUTIONS: dict[tuple[int, int], tuple[int, int]] = {
    (9, 16): (1080, 1920),
    (1, 1): (1080, 1080),
    (4, 5): (1080, 1350),
    (16, 9): (1920, 1080),
}


@dataclass(frozen=True)
class ReframeTarget:
    """One output variant to render from a tracked path."""

    aspect: tuple[int, int]
    resolution: tuple[int, int]
    label: str  # e.g. "9x16", "1x1"
    platforms: tuple[str, ...] = ()


def aspect_label(aspect: tuple[int, int]) -> str:
    return f"{aspect[0]}x{aspect[1]}"


def platforms_to_targets(platforms: list[str]) -> list[ReframeTarget]:
    """Convert selected platform names into unique aspect targets."""
    seen: dict[tuple[int, int], ReframeTarget] = {}
    for name in platforms:
        spec = PLATFORM_SPECS.get(name)
        if spec is None:
            continue
        aspect, resolution = spec
        if aspect in seen:
            existing = seen[aspect]
            seen[aspect] = ReframeTarget(
                aspect=aspect,
                resolution=resolution,
                label=existing.label,
                platforms=existing.platforms + (name,),
            )
        else:
            seen[aspect] = ReframeTarget(
                aspect=aspect,
                resolution=resolution,
                label=aspect_label(aspect),
                platforms=(name,),
            )
    return list(seen.values())


def default_targets() -> list[ReframeTarget]:
    """Default: 9:16 portrait for Shorts/TikTok/Reels."""
    aspect = (9, 16)
    return [ReframeTarget(
        aspect=aspect,
        resolution=ASPECT_RESOLUTIONS[aspect],
        label=aspect_label(aspect),
        platforms=("YouTube Shorts", "TikTok", "Instagram Reels"),
    )]
