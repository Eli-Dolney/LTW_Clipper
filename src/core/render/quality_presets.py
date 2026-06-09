"""Centralized ffmpeg quality presets for splitter, Opus pipeline, and optimizers."""

from __future__ import annotations

from typing import TypedDict


class QualitySpec(TypedDict, total=False):
    description: str
    resolution: str | None
    bitrate: str | None
    crf: int
    preset: str


QUALITY_PRESETS: dict[str, QualitySpec] = {
    "youtube_sd": {
        "description": "YouTube SD (720p)",
        "resolution": "1280:720",
        "bitrate": "2500k",
        "crf": 23,
        "preset": "medium",
    },
    "youtube_hd": {
        "description": "YouTube HD (1080p)",
        "resolution": "1920:1080",
        "bitrate": "5000k",
        "crf": 20,
        "preset": "medium",
    },
    "youtube_4k": {
        "description": "YouTube 4K (2160p)",
        "resolution": "3840:2160",
        "bitrate": "15000k",
        "crf": 18,
        "preset": "slow",
    },
    "shorts_1080p": {
        "description": "Vertical Shorts 1080x1920",
        "resolution": "1080:1920",
        "bitrate": "6000k",
        "crf": 20,
        "preset": "medium",
    },
    "original": {
        "description": "Original resolution (high bitrate)",
        "resolution": None,
        "bitrate": "8000k",
        "crf": 18,
        "preset": "slow",
    },
}


def get_quality(name: str) -> QualitySpec:
    if name not in QUALITY_PRESETS:
        raise KeyError(f"Unknown quality preset: {name}. Choose from {list(QUALITY_PRESETS)}")
    return QUALITY_PRESETS[name]


def quality_names() -> list[str]:
    return list(QUALITY_PRESETS.keys())
