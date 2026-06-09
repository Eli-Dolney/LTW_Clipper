"""Channel templates: niche-specific presets that drive the whole pipeline.

A :class:`ChannelTemplate` sits *above* the older GUI ``Preset`` concept. Where
a preset only tuned splitting (duration / quality / LUT), a template also feeds:

- the heuristic scorer (niche-specific ``hook_phrases`` / ``hook_words`` / weights)
- the metadata writer (``persona`` / ``tone`` / ``title_style`` / hashtags)
- the look & sound layer (caption preset, LUT, transition + SFX packs)

Templates are plain JSON in ``assets/templates`` (built-ins) plus a user
directory for custom/edited ones. Everything is local and free.
"""

from .models import (
    ChannelTemplate,
    ScoringWeightsModel,
    VoiceProfile,
    LookAndSound,
)
from .manager import TemplateManager

__all__ = [
    "ChannelTemplate",
    "ScoringWeightsModel",
    "VoiceProfile",
    "LookAndSound",
    "TemplateManager",
]
