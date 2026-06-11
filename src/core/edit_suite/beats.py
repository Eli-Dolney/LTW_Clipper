"""Beat detection for music-synced edits."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import BeatMap

log = logging.getLogger(__name__)


def detect_beats(audio_path: Path, output_path: Path | None = None) -> BeatMap:
    """Analyze an audio file and return beat timestamps."""
    try:
        import librosa
    except ImportError as exc:
        raise RuntimeError("librosa is required for beat detection") from exc

    audio_path = Path(audio_path)
    if not audio_path.is_file():
        raise FileNotFoundError(audio_path)

    log.info("Analyzing beats: %s", audio_path.name)
    y, sr = librosa.load(str(audio_path))
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    beat_map = BeatMap(
        source=str(audio_path),
        tempo=float(tempo),
        total_beats=len(beat_times),
        beats=[float(t) for t in beat_times],
    )

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(beat_map.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
    return beat_map


def load_beat_map(path: Path) -> BeatMap:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return BeatMap.model_validate(data)
