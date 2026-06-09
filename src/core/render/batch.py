"""Parallel ffmpeg clip rendering via ProcessPoolExecutor."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClipRenderJob:
    """Serializable job for worker processes."""

    source: str
    output: str
    start: float
    end: float
    crf: int = 20
    preset: str = "medium"
    video_encoder: str | None = None


def _worker_extract(job: ClipRenderJob) -> tuple[str, bool, str]:
    """Extract one clip; returns (output_path, ok, error_message)."""
    try:
        from .ffmpeg import FFmpegRunner

        runner = FFmpegRunner(video_encoder=job.video_encoder)
        runner.extract_clip(
            Path(job.source),
            Path(job.output),
            start=job.start,
            end=job.end,
            crf=job.crf,
            preset=job.preset,
        )
        return job.output, True, ""
    except Exception as exc:  # noqa: BLE001
        return job.output, False, str(exc)


def default_concurrency(requested: int = 0) -> int:
    if requested > 0:
        return requested
    cpus = os.cpu_count() or 4
    return max(1, cpus // 2)


def render_clips_parallel(
    jobs: list[ClipRenderJob],
    *,
    concurrency: int = 0,
    on_complete: Callable[[str, bool, str], None] | None = None,
) -> dict[str, tuple[bool, str]]:
    """Run extract jobs in parallel. Returns {output: (ok, err)}."""
    if not jobs:
        return {}

    workers = min(default_concurrency(concurrency), len(jobs))
    results: dict[str, tuple[bool, str]] = {}

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_worker_extract, j): j for j in jobs}
        for fut in as_completed(futures):
            out, ok, err = fut.result()
            results[out] = (ok, err)
            if on_complete:
                on_complete(out, ok, err)
            if not ok:
                log.warning("Parallel extract failed for %s: %s", out, err)

    return results
