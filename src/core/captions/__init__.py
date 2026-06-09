"""Caption generation and burn-in utilities.

- ``styler`` converts Whisper word-timestamps into stylized ASS/SRT/VTT files.
- ``burner`` drives ffmpeg to burn ASS captions into a video copy.

All local. No cloud services.
"""

from .styler import CaptionStyle, CaptionStyler, CAPTION_PRESETS
from .burner import CaptionBurner

__all__ = ["CaptionStyle", "CaptionStyler", "CAPTION_PRESETS", "CaptionBurner"]
