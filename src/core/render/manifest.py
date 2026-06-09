"""Resumable run manifest with atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ClipManifestEntry:
    slug: str
    start: float
    end: float
    status: str = "pending"  # pending | rendering | done | failed
    clip_dir: str = ""
    error: str = ""


@dataclass
class RunManifest:
    source_video: str
    project_name: str
    run_id: str
    generator: str = ""
    stage: str = "probe"  # probe | transcribe | plan | render | package | done
    clips: list[ClipManifestEntry] = field(default_factory=list)
    completed_slugs: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_video": self.source_video,
            "project_name": self.project_name,
            "run_id": self.run_id,
            "generator": self.generator,
            "stage": self.stage,
            "clips": [
                {
                    "slug": c.slug,
                    "start": c.start,
                    "end": c.end,
                    "status": c.status,
                    "clip_dir": c.clip_dir,
                    "error": c.error,
                }
                for c in self.clips
            ],
            "completed_slugs": list(self.completed_slugs),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunManifest":
        clips = [
            ClipManifestEntry(
                slug=c["slug"],
                start=float(c["start"]),
                end=float(c["end"]),
                status=c.get("status", "pending"),
                clip_dir=c.get("clip_dir", ""),
                error=c.get("error", ""),
            )
            for c in data.get("clips", [])
        ]
        return cls(
            source_video=data["source_video"],
            project_name=data["project_name"],
            run_id=data["run_id"],
            generator=data.get("generator", ""),
            stage=data.get("stage", "probe"),
            clips=clips,
            completed_slugs=list(data.get("completed_slugs", [])),
            updated_at=data.get("updated_at", ""),
        )


def load_manifest(path: Path) -> RunManifest | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return RunManifest.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def save_manifest(path: Path, manifest: RunManifest) -> None:
    """Atomically write manifest.json (write temp + rename)."""
    manifest.updated_at = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest.to_dict(), indent=2)
    fd, tmp = tempfile.mkstemp(prefix=".manifest_", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def pending_clips(manifest: RunManifest) -> list[ClipManifestEntry]:
    done = set(manifest.completed_slugs)
    return [c for c in manifest.clips if c.slug not in done and c.status != "done"]
