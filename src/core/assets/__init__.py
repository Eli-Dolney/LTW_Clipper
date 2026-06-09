"""Asset packs: user-added folders of transitions, SFX, overlays and music.

The user (or anyone running the tool) clicks "Add folder" and points at wherever
their DaVinci transition / SFX packs live — a local folder, an external drive, a
synced Google Drive folder, etc. We never copy the media; we just index whatever
files are present so templates and the render pipeline can reference them by name.
"""

from .pack_manager import AssetItem, AssetPack, AssetPackManager, AssetKind

__all__ = ["AssetItem", "AssetPack", "AssetPackManager", "AssetKind"]
