"""Tests for the asset pack registry + scanner."""

from __future__ import annotations

from pathlib import Path

from src.core.assets import AssetPackManager


def _make_pack(tmp_path: Path) -> Path:
    pack = tmp_path / "whoosh_pack"
    pack.mkdir()
    (pack / "whoosh1.wav").write_bytes(b"RIFF0000")
    (pack / "whoosh2.mp3").write_bytes(b"ID3")
    (pack / "swipe.mov").write_bytes(b"\x00\x00\x00\x18ftyp")
    (pack / "glow.png").write_bytes(b"\x89PNG")
    (pack / "readme.txt").write_text("not media")
    return pack


def test_add_scan_and_classify(tmp_path: Path) -> None:
    mgr = AssetPackManager(registry_path=tmp_path / "reg.json")
    pack_dir = _make_pack(tmp_path)
    pack = mgr.add_folder(pack_dir, kind="auto")

    assert pack.available is True
    # readme.txt ignored; 4 media files classified.
    kinds = {i.kind for i in pack.items}
    assert "sfx" in kinds  # wav + mp3
    assert "transition" in kinds  # mov
    assert "overlay" in kinds  # png
    assert len(pack.items) == 4

    sfx = mgr.items("sfx")
    assert {i.ext for i in sfx} == {".wav", ".mp3"}


def test_registry_persists(tmp_path: Path) -> None:
    reg = tmp_path / "reg.json"
    pack_dir = _make_pack(tmp_path)
    AssetPackManager(registry_path=reg).add_folder(pack_dir, kind="sfx", name="My SFX")

    reloaded = AssetPackManager(registry_path=reg)
    assert "My SFX" in reloaded.pack_names()
    # declared kind forces all items to that kind
    items = reloaded.items()
    assert items and all(i.kind == "sfx" for i in items)


def test_remove_and_enabled(tmp_path: Path) -> None:
    reg = tmp_path / "reg.json"
    pack_dir = _make_pack(tmp_path)
    mgr = AssetPackManager(registry_path=reg)
    mgr.add_folder(pack_dir, name="P")
    mgr.set_enabled(pack_dir, False)
    assert mgr.items(enabled_only=True) == []
    assert mgr.remove_folder(pack_dir) is True
    assert mgr.pack_names() == []


def test_offline_folder_is_unavailable(tmp_path: Path) -> None:
    mgr = AssetPackManager(registry_path=tmp_path / "reg.json")
    pack = mgr.add_folder(tmp_path / "does_not_exist_yet", name="Cloud")
    assert pack.available is False
    assert pack.items == []
    # Still registered so it can come back online later.
    assert "Cloud" in mgr.pack_names()
