"""Tests for atomic manifest read/write."""

from __future__ import annotations

from pathlib import Path

from src.core.render.manifest import ClipManifestEntry, RunManifest, load_manifest, save_manifest


def test_manifest_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    m = RunManifest(
        source_video="/tmp/video.mp4",
        project_name="test",
        run_id="run1",
        generator="heuristic",
        stage="render",
        clips=[ClipManifestEntry(slug="clip-a", start=0.0, end=10.0, status="pending")],
        completed_slugs=[],
    )
    save_manifest(path, m)
    loaded = load_manifest(path)
    assert loaded is not None
    assert loaded.project_name == "test"
    assert len(loaded.clips) == 1
    assert loaded.clips[0].slug == "clip-a"
