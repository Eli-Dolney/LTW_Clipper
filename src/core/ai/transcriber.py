"""Local speech-to-text via ``faster-whisper``.

No cloud. Models cache under ``~/.cache/ltw/whisper/`` by default.
``faster-whisper`` is a CTranslate2 reimplementation of Whisper that is 2-4x
faster than OpenAI's reference on CPU and supports word-level timestamps.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from ..models import Transcript, TranscriptSegment, WordTiming

log = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "ltw" / "whisper"


@dataclass(frozen=True)
class TranscriberConfig:
    model: str = "small"            # tiny | base | small | medium | large-v3
    device: str = "auto"             # auto | cpu | cuda | mps
    compute_type: str = "auto"       # auto | int8 | int8_float16 | float16 | float32
    vad_filter: bool = True
    language: str | None = None
    cache_dir: Path = DEFAULT_CACHE_DIR


class LocalTranscriber:
    """Thin wrapper over ``faster_whisper.WhisperModel``.

    The underlying library is imported lazily so the rest of the pipeline
    (GUI, splitter) works on systems that haven't installed it yet.
    """

    def __init__(self, config: TranscriberConfig | None = None) -> None:
        self.config = config or TranscriberConfig()
        self._model = None  # type: ignore[assignment]

    # ---- Loading -----------------------------------------------------------

    def _resolve_device_and_compute(self) -> tuple[str, str]:
        device = self.config.device
        compute_type = self.config.compute_type

        if device == "auto":
            try:
                import torch  # type: ignore

                if torch.cuda.is_available():
                    device = "cuda"
                elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                    # faster-whisper doesn't support MPS directly; CPU int8 is fastest on Apple Silicon.
                    device = "cpu"
                else:
                    device = "cpu"
            except Exception:
                device = "cpu"

        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        return device, compute_type

    def _load(self):
        if self._model is not None:
            return self._model

        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:  # pragma: no cover - install-time error
            raise RuntimeError(
                "faster-whisper is not installed. Run `pip install faster-whisper`."
            ) from exc

        device, compute_type = self._resolve_device_and_compute()
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)
        log.info(
            "Loading Whisper model=%s device=%s compute=%s",
            self.config.model, device, compute_type,
        )
        self._model = WhisperModel(
            self.config.model,
            device=device,
            compute_type=compute_type,
            download_root=str(self.config.cache_dir),
        )
        return self._model

    # ---- Public API --------------------------------------------------------

    def transcribe(self, audio_path: Path) -> Transcript:
        """Transcribe a media file and return a :class:`Transcript`.

        ``audio_path`` may be any format ffmpeg can read (mp4, mov, wav, ...).
        """
        if not audio_path.exists():
            raise FileNotFoundError(audio_path)

        model = self._load()

        segments_iter, info = model.transcribe(
            str(audio_path),
            word_timestamps=True,
            vad_filter=self.config.vad_filter,
            language=self.config.language or None,
        )

        segments: list[TranscriptSegment] = []
        for seg in segments_iter:
            words: list[WordTiming] = []
            for w in getattr(seg, "words", None) or []:
                words.append(
                    WordTiming(
                        word=(w.word or "").strip(),
                        start=float(w.start or seg.start),
                        end=float(w.end or seg.end),
                        probability=float(getattr(w, "probability", 1.0)),
                    )
                )
            segments.append(
                TranscriptSegment(
                    id=int(seg.id),
                    start=float(seg.start),
                    end=float(seg.end),
                    text=seg.text.strip(),
                    words=words,
                )
            )

        return Transcript(
            language=info.language or "",
            duration=float(info.duration or 0.0),
            segments=segments,
        )

    # ---- Convenience -------------------------------------------------------

    @staticmethod
    def _default_cache_dir() -> Path:
        """Respect ``LTW_WHISPER_CACHE`` env var for testing."""
        override = os.environ.get("LTW_WHISPER_CACHE")
        return Path(override) if override else DEFAULT_CACHE_DIR
