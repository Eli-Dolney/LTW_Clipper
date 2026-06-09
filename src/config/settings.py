"""Typed runtime configuration for LTW Splitter Pro.

Loads settings from (in order of precedence):
1. Environment variables prefixed with ``LTW_`` (e.g. ``LTW_WHISPER__MODEL=small``).
2. ``config/settings.yaml`` at the project root, if present.
3. ``config/settings.example.yaml`` as a last-resort fallback.
4. Hard-coded defaults defined below.

Everything is local. No API keys.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


# ----- Repo discovery -------------------------------------------------------

def _repo_root() -> Path:
    """Project root is two parents up from this file (src/config/settings.py)."""
    return Path(__file__).resolve().parents[2]


# ----- Section models -------------------------------------------------------

class AppSettings(BaseModel):
    output_root: Path = Field(default=Path("~/Desktop/clips"))
    render_concurrency: int = 0

    def resolved_output_root(self) -> Path:
        return Path(os.path.expandvars(str(self.output_root))).expanduser()


class FfmpegSettings(BaseModel):
    binary: str = "auto"
    hwaccel: Literal["auto", "videotoolbox", "nvenc", "qsv", "vaapi", "cpu"] = "auto"


class WhisperSettings(BaseModel):
    model: Literal["tiny", "base", "small", "medium", "large-v3"] = "small"
    device: Literal["auto", "cuda", "mps", "cpu"] = "auto"
    compute_type: str = "auto"
    vad_filter: bool = True
    language: str = ""


class OllamaSettings(BaseModel):
    enabled: bool = True
    host: str = "http://localhost:11434"
    model: str = "llama3.1:8b"
    request_timeout: int = 120


class ReframeSettings(BaseModel):
    target_aspect: str = "9:16"
    layout: Literal["crop", "fit", "blur"] = "crop"
    smoothing: float = 0.35
    deadzone: float = 0.04
    headroom: float = 0.08
    zoom: float = 1.0
    max_pan_speed: float = 0.18

    def parse_aspect(self) -> tuple[int, int]:
        parts = self.target_aspect.split(":")
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
        return 9, 16


class CaptionsSettings(BaseModel):
    preset: str = "bold_outline"
    burn_in: bool = True
    export_sidecar: bool = True


class LoggingSettings(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    json_file: bool = True


# ----- Root model -----------------------------------------------------------

class Settings(BaseModel):
    app: AppSettings = Field(default_factory=AppSettings)
    ffmpeg: FfmpegSettings = Field(default_factory=FfmpegSettings)
    whisper: WhisperSettings = Field(default_factory=WhisperSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    reframe: ReframeSettings = Field(default_factory=ReframeSettings)
    captions: CaptionsSettings = Field(default_factory=CaptionsSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @classmethod
    def load(cls, explicit_path: Path | None = None) -> "Settings":
        root = _repo_root()
        candidates: list[Path] = []
        if explicit_path is not None:
            candidates.append(Path(explicit_path))
        candidates.extend([
            root / "config" / "settings.yaml",
            root / "config" / "settings.example.yaml",
        ])

        data: dict = {}
        for path in candidates:
            if path.is_file():
                with path.open("r", encoding="utf-8") as fh:
                    loaded = yaml.safe_load(fh) or {}
                if isinstance(loaded, dict):
                    data = loaded
                    break

        data = _apply_env_overrides(data)
        return cls.model_validate(data)


# ----- Env override helper --------------------------------------------------

def _apply_env_overrides(data: dict) -> dict:
    """Apply LTW_SECTION__KEY=value overrides onto the nested dict."""
    prefix = "LTW_"
    for env_key, env_val in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        path = env_key[len(prefix):].lower().split("__")
        cursor = data
        for piece in path[:-1]:
            cursor = cursor.setdefault(piece, {})
            if not isinstance(cursor, dict):
                break
        else:
            cursor[path[-1]] = _coerce(env_val)
    return data


def _coerce(val: str):
    low = val.strip().lower()
    if low in {"true", "yes", "1"}:
        return True
    if low in {"false", "no", "0"}:
        return False
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


# ----- Public API -----------------------------------------------------------

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton Settings instance."""
    return Settings.load()
