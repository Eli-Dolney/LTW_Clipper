"""Caption generation and burn-in utilities.

- ``styler`` converts Whisper word-timestamps into stylized ASS/SRT/VTT files.
- ``burner`` drives ffmpeg to burn ASS captions into a video copy.
- ``style_manager`` loads/saves editable caption style JSON templates.
- ``preview`` renders live style previews for the Text Studio GUI.

All local. No cloud services.
"""

from .burner import CaptionBurner
from .models import CaptionStyleModel, TextOverlayModel
from .style_manager import StyleManager
from .styler import CAPTION_PRESETS, CaptionStyle, CaptionStyler

__all__ = [
    "CaptionBurner",
    "CaptionStyle",
    "CaptionStyleModel",
    "CaptionStyler",
    "CAPTION_PRESETS",
    "StyleManager",
    "TextOverlayModel",
]
