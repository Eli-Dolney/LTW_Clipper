"""Load, save, import and export :class:`ChannelTemplate` definitions.

Built-in templates ship as JSON under ``assets/templates`` (flagged
``"builtin": true``). User-created / edited templates are saved to the same
directory so they show up automatically next launch. Built-ins cannot be
deleted; saving over a built-in name creates a user copy that shadows it.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import ChannelTemplate

log = logging.getLogger(__name__)


def _default_templates_dir() -> Path:
    # repo_root/assets/templates  (manager.py -> templates -> core -> src -> root)
    return Path(__file__).resolve().parents[3] / "assets" / "templates"


class TemplateManager:
    """In-memory registry of channel templates backed by JSON on disk."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        self.templates_dir = Path(templates_dir) if templates_dir else _default_templates_dir()
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._templates: dict[str, ChannelTemplate] = {}
        self.reload()

    # ---- Loading -----------------------------------------------------------

    def reload(self) -> None:
        self._templates.clear()
        for path in sorted(self.templates_dir.glob("*.json")):
            tpl = self._load_file(path)
            if tpl is not None:
                self._templates[tpl.name] = tpl

    def _load_file(self, path: Path) -> ChannelTemplate | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ChannelTemplate.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load template %s: %s", path.name, exc)
            return None

    # ---- Queries -----------------------------------------------------------

    def get(self, name: str) -> ChannelTemplate | None:
        return self._templates.get(name)

    def all(self) -> list[ChannelTemplate]:
        return sorted(self._templates.values(), key=lambda t: (not t.builtin, t.name.lower()))

    def by_niche(self, niche: str) -> list[ChannelTemplate]:
        return [t for t in self._templates.values() if t.niche == niche]

    def niches(self) -> list[str]:
        return sorted({t.niche for t in self._templates.values()})

    def names(self) -> list[str]:
        return [t.name for t in self.all()]

    # ---- Mutations ---------------------------------------------------------

    def save(self, template: ChannelTemplate) -> Path:
        """Persist a template to disk. User saves are never flagged built-in."""
        template.builtin = False
        template.touch()
        path = self.templates_dir / f"{template.slug}.json"
        path.write_text(
            json.dumps(template.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        self._templates[template.name] = template
        return path

    def delete(self, name: str) -> bool:
        tpl = self._templates.get(name)
        if tpl is None or tpl.builtin:
            return False
        path = self.templates_dir / f"{tpl.slug}.json"
        if path.exists():
            path.unlink()
        del self._templates[name]
        return True

    def export(self, name: str, dest: Path) -> bool:
        tpl = self._templates.get(name)
        if tpl is None:
            return False
        Path(dest).write_text(
            json.dumps(tpl.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return True

    def import_file(self, src: Path) -> ChannelTemplate | None:
        try:
            data = json.loads(Path(src).read_text(encoding="utf-8"))
            tpl = ChannelTemplate.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to import template %s: %s", src, exc)
            return None
        self.save(tpl)
        return tpl
