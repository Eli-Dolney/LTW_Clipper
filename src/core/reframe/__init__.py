"""Smart 9:16 (and other aspect) reframing pipeline.

- ``tracker`` produces a time-series of crop windows using MediaPipe faces
  (required) with an OpenCV-only degraded path if MediaPipe fails at runtime.
- ``renderer`` consumes the time-series and drives ffmpeg to produce the
  reframed output with crop/fit/blur layouts.
- ``platform_specs`` maps GUI platform names to aspect ratios and resolutions.
"""

from .platform_specs import ReframeTarget, platforms_to_targets, default_targets
from .renderer import LayoutMode, ReframeRenderer, RenderConfig, interpolate_windows
from .tracker import CropWindow, ReframeTracker, TrackerConfig, TrackedReframe

__all__ = [
    "CropWindow",
    "ReframeRenderer",
    "ReframeTarget",
    "ReframeTracker",
    "RenderConfig",
    "TrackerConfig",
    "TrackedReframe",
    "LayoutMode",
    "default_targets",
    "interpolate_windows",
    "platforms_to_targets",
]
