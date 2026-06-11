"""Load, save, import and export caption style definitions."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import CaptionStyleModel
from .styler import CAPTION_PRESETS

log = logging.getLogger(__name__)


def _default_styles_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "assets" / "caption_styles"


class StyleManager:
    """In-memory registry of caption styles backed by JSON on disk."""

    def __init__(self, styles_dir: Path | None = None) -> None:
        self.styles_dir = Path(styles_dir) if styles_dir else _default_styles_dir()
        self.styles_dir.mkdir(parents=True, exist_ok=True)
        self._styles: dict[str, CaptionStyleModel] = {}
        self.reload()

    def reload(self) -> None:
        self._styles.clear()
        for path in sorted(self.styles_dir.glob("*.json")):
            style = self._load_file(path)
            if style is not None:
                self._styles[style.name] = style
        if not self._styles:
            for name, style in CAPTION_PRESETS.items():
                self._styles[name] = style

    def _load_file(self, path: Path) -> CaptionStyleModel | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CaptionStyleModel.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load caption style %s: %s", path.name, exc)
            return None

    def get(self, name: str) -> CaptionStyleModel | None:
        return self._styles.get(name)

    def all(self) -> list[CaptionStyleModel]:
        return sorted(self._styles.values(), key=lambda s: (not s.builtin, s.name.lower()))

    def names(self) -> list[str]:
        return [s.name for s in self.all()]

    def save(self, style: CaptionStyleModel) -> Path:
        style.builtin = False
        path = self.styles_dir / f"{style.slug}.json"
        path.write_text(
            json.dumps(style.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        self._styles[style.name] = style
        return path

    def delete(self, name: str) -> bool:
        style = self._styles.get(name)
        if style is None or style.builtin:
            return False
        path = self.styles_dir / f"{style.slug}.json"
        if path.exists():
            path.unlink()
        del self._styles[name]
        return True

    def duplicate(self, name: str, new_name: str) -> CaptionStyleModel | None:
        source = self._styles.get(name)
        if source is None:
            return None
        copy = source.model_copy(deep=True)
        copy.name = new_name
        copy.builtin = False
        self.save(copy)
        return copy

    def export(self, name: str, dest: Path) -> bool:
        style = self._styles.get(name)
        if style is None:
            return False
        Path(dest).write_text(
            json.dumps(style.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return True

    def import_file(self, src: Path) -> CaptionStyleModel | None:
        try:
            data = json.loads(Path(src).read_text(encoding="utf-8"))
            style = CaptionStyleModel.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to import caption style %s: %s", src, exc)
            return None
        self.save(style)
        return style

    def resolve(self, preset_name: str, inline_style: CaptionStyleModel | None = None) -> CaptionStyleModel:
        """Prefer inline style, then named preset, then built-in fallback."""
        if inline_style is not None:
            return inline_style
        style = self.get(preset_name)
        if style is not None:
            return style
        if preset_name in CAPTION_PRESETS:
            return CAPTION_PRESETS[preset_name]
        raise ValueError(f"Unknown caption style: {preset_name}")
