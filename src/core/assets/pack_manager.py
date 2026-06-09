"""Index and manage user-added asset pack folders.

A *pack* is just a folder the user added. We persist a small registry of those
folders (path + declared kind + friendly name) and, on demand, scan each folder
for supported media. Folders that are offline (e.g. an unsynced cloud drive or
an unplugged external disk) are reported as unavailable rather than erroring.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

log = logging.getLogger(__name__)

AssetKind = Literal["transition", "sfx", "music", "overlay"]

VIDEO_EXTS = {".mov", ".mp4", ".webm", ".mkv", ".avi", ".m4v"}
AUDIO_EXTS = {".wav", ".mp3", ".aif", ".aiff", ".m4a", ".flac", ".ogg"}
IMAGE_EXTS = {".png", ".tga", ".tif", ".tiff", ".webp", ".gif"}
ALL_EXTS = VIDEO_EXTS | AUDIO_EXTS | IMAGE_EXTS


def _classify(ext: str) -> AssetKind:
    ext = ext.lower()
    if ext in AUDIO_EXTS:
        return "sfx"
    if ext in IMAGE_EXTS:
        return "overlay"
    return "transition"


@dataclass
class AssetItem:
    name: str
    path: Path
    kind: AssetKind
    ext: str
    size: int = 0


@dataclass
class AssetPack:
    name: str
    root: Path
    kind: str  # declared kind ("auto" allowed) — items carry resolved kinds
    enabled: bool = True
    available: bool = False
    items: list[AssetItem] = field(default_factory=list)

    def by_kind(self, kind: AssetKind) -> list[AssetItem]:
        return [i for i in self.items if i.kind == kind]


def _default_registry_path() -> Path:
    # repo_root/config/asset_packs.json
    return Path(__file__).resolve().parents[3] / "config" / "asset_packs.json"


class AssetPackManager:
    """Registry + scanner for asset pack folders."""

    def __init__(self, registry_path: Path | None = None, *, recursive: bool = True) -> None:
        self.registry_path = Path(registry_path) if registry_path else _default_registry_path()
        self.recursive = recursive
        self._registry: list[dict] = []
        self._load_registry()

    # ---- Registry persistence ---------------------------------------------

    def _load_registry(self) -> None:
        if self.registry_path.exists():
            try:
                data = json.loads(self.registry_path.read_text(encoding="utf-8"))
                self._registry = data.get("folders", []) if isinstance(data, dict) else []
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to read asset pack registry: %s", exc)
                self._registry = []
        else:
            self._registry = []

    def _save_registry(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(
            json.dumps({"folders": self._registry}, indent=2),
            encoding="utf-8",
        )

    # ---- Folder management -------------------------------------------------

    def add_folder(
        self,
        path: str | Path,
        kind: str = "auto",
        name: str | None = None,
    ) -> AssetPack:
        """Register a folder. Idempotent on path; updates kind/name if re-added."""
        p = Path(path).expanduser()
        resolved = str(p)
        entry = {"path": resolved, "kind": kind, "name": name or p.name, "enabled": True}
        for existing in self._registry:
            if existing.get("path") == resolved:
                existing.update(entry)
                self._save_registry()
                return self._scan_entry(existing)
        self._registry.append(entry)
        self._save_registry()
        return self._scan_entry(entry)

    def remove_folder(self, path: str | Path) -> bool:
        resolved = str(Path(path).expanduser())
        before = len(self._registry)
        self._registry = [e for e in self._registry if e.get("path") != resolved]
        if len(self._registry) != before:
            self._save_registry()
            return True
        return False

    def set_enabled(self, path: str | Path, enabled: bool) -> None:
        resolved = str(Path(path).expanduser())
        for e in self._registry:
            if e.get("path") == resolved:
                e["enabled"] = enabled
        self._save_registry()

    def folders(self) -> list[dict]:
        return list(self._registry)

    # ---- Scanning ----------------------------------------------------------

    def _scan_entry(self, entry: dict) -> AssetPack:
        root = Path(entry["path"]).expanduser()
        declared = entry.get("kind", "auto")
        pack = AssetPack(
            name=entry.get("name") or root.name,
            root=root,
            kind=declared,
            enabled=bool(entry.get("enabled", True)),
        )
        if not root.exists() or not root.is_dir():
            pack.available = False
            return pack
        pack.available = True
        globber = root.rglob("*") if self.recursive else root.glob("*")
        for f in sorted(globber):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            if ext not in ALL_EXTS:
                continue
            item_kind: AssetKind = _classify(ext) if declared == "auto" else declared  # type: ignore[assignment]
            try:
                size = f.stat().st_size
            except OSError:
                size = 0
            pack.items.append(AssetItem(name=f.stem, path=f, kind=item_kind, ext=ext, size=size))
        return pack

    def packs(self, *, enabled_only: bool = False) -> list[AssetPack]:
        out = [self._scan_entry(e) for e in self._registry]
        if enabled_only:
            out = [p for p in out if p.enabled]
        return out

    def get_pack(self, name: str) -> AssetPack | None:
        for e in self._registry:
            if (e.get("name") or "") == name:
                return self._scan_entry(e)
        return None

    def items(self, kind: AssetKind | None = None, *, enabled_only: bool = True) -> list[AssetItem]:
        out: list[AssetItem] = []
        for pack in self.packs(enabled_only=enabled_only):
            if not pack.available:
                continue
            out.extend(pack.items if kind is None else pack.by_kind(kind))
        return out

    def pack_names(self, kind: str | None = None) -> list[str]:
        names: list[str] = []
        for e in self._registry:
            if kind and e.get("kind") not in (kind, "auto"):
                continue
            n = e.get("name") or Path(e["path"]).name
            if n not in names:
                names.append(n)
        return names
