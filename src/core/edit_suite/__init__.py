"""Sports/movie edit suite — beat sync, audio layering, reference replication."""

from .audio_mixer import AudioMixOptions, AudioMixer, build_audio_mix_filtergraph
from .beats import detect_beats
from .models import BeatMap
from .composer import EditComposer, EditComposeOptions
from .models import EditStyleRecipe, ReferenceAnalysis
from .reference_analyzer import ReferenceAnalyzer

__all__ = [
    "AudioMixOptions",
    "AudioMixer",
    "BeatMap",
    "EditComposeOptions",
    "EditComposer",
    "EditStyleRecipe",
    "ReferenceAnalysis",
    "ReferenceAnalyzer",
    "build_audio_mix_filtergraph",
    "detect_beats",
]
