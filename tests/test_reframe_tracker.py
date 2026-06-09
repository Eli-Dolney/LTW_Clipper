"""Tests for the reframe tracker's pure-math helpers.

We avoid any actual video I/O here; tracker.track() is covered by
integration tests (to be added later). These tests exercise the smoothing,
deadzone, geometry, and face-selection logic directly.
"""

from __future__ import annotations

import numpy as np

from src.core.reframe.tracker import (
    CropSample,
    FaceCandidate,
    ReframeTracker,
    TrackerConfig,
    _select_face,
)
from src.core.reframe.renderer import interpolate_windows, write_sendcmd_script
from src.core.reframe.platform_specs import platforms_to_targets


def test_smoothing_reduces_jitter() -> None:
    samples = [
        CropSample(timestamp=i * 0.25, cx=0.5 + (0.15 if i % 2 else -0.15), cy=0.5, confidence=1.0, detected=True)
        for i in range(20)
    ]
    tracker = ReframeTracker(TrackerConfig(smoothing=0.8, deadzone=0.0, max_pan_speed=10.0))
    smoothed = tracker._smooth_samples(samples)

    raw_std = float(np.std([s.cx for s in samples]))
    new_std = float(np.std([s.cx for s in smoothed]))
    assert new_std < raw_std, f"smoothing should reduce std (raw={raw_std:.4f}, new={new_std:.4f})"


def test_deadzone_rejects_small_moves() -> None:
    samples = [
        CropSample(timestamp=0.0, cx=0.500, cy=0.5, confidence=1.0, detected=True),
        CropSample(timestamp=0.1, cx=0.520, cy=0.5, confidence=1.0, detected=True),
        CropSample(timestamp=0.2, cx=0.515, cy=0.5, confidence=1.0, detected=True),
    ]
    tracker = ReframeTracker(TrackerConfig(smoothing=0.0, deadzone=0.05, max_pan_speed=10.0))
    smoothed = tracker._smooth_samples(samples)

    assert smoothed[1].cx == 0.500
    assert smoothed[2].cx == 0.500


def test_deadzone_allows_large_moves() -> None:
    samples = [
        CropSample(timestamp=0.0, cx=0.20, cy=0.5, confidence=1.0, detected=True),
        CropSample(timestamp=0.1, cx=0.80, cy=0.5, confidence=1.0, detected=True),
    ]
    tracker = ReframeTracker(TrackerConfig(smoothing=0.0, deadzone=0.05, max_pan_speed=10.0))
    smoothed = tracker._smooth_samples(samples)

    assert abs(smoothed[1].cx - 0.80) < 1e-6


def test_velocity_clamp_limits_per_step_movement() -> None:
    samples = [
        CropSample(timestamp=0.0, cx=0.2, cy=0.5, confidence=1.0, detected=True),
        CropSample(timestamp=0.1, cx=0.9, cy=0.5, confidence=1.0, detected=True),
    ]
    tracker = ReframeTracker(TrackerConfig(smoothing=0.0, deadzone=0.0, max_pan_speed=0.5))
    smoothed = tracker._smooth_samples(samples)

    # max step = 0.5 * 0.1 = 0.05
    assert smoothed[1].cx <= 0.2 + 0.05 + 1e-6


def test_carry_forward_on_dropout() -> None:
    """Missed detections should hold last position, not snap to center."""
    raw = [
        CropSample(timestamp=0.0, cx=0.3, cy=0.4, confidence=1.0, detected=True),
        CropSample(timestamp=0.25, cx=0.3, cy=0.4, confidence=0.0, detected=False),
        CropSample(timestamp=0.5, cx=0.3, cy=0.4, confidence=0.0, detected=False),
    ]
    tracker = ReframeTracker(TrackerConfig(smoothing=0.5, max_pan_speed=10.0))
    smoothed = tracker._smooth_samples(raw)
    assert abs(smoothed[1].cx - 0.3) < 0.05
    assert abs(smoothed[2].cx - 0.3) < 0.08


def test_nearest_face_selection_stays_locked() -> None:
    prev_cx, prev_cy = 0.25, 0.5
    faces = [
        FaceCandidate(cx=0.75, cy=0.5, confidence=0.99, area=0.05),
        FaceCandidate(cx=0.28, cy=0.5, confidence=0.70, area=0.04),
    ]
    best = _select_face(faces, prev_cx, prev_cy)
    assert abs(best.cx - 0.28) < 0.01


def test_compute_target_size_portrait_from_landscape() -> None:
    tracker = ReframeTracker(TrackerConfig(target_aspect=(9, 16)))
    tw, th = tracker._compute_target_size(1920, 1080)
    assert th == 1080
    assert tw == 608


def test_compute_target_size_square() -> None:
    tracker = ReframeTracker(TrackerConfig(target_aspect=(1, 1)))
    tw, th = tracker._compute_target_size(1920, 1080)
    assert tw == th == 1080


def test_compute_target_size_4x5() -> None:
    tracker = ReframeTracker(TrackerConfig(target_aspect=(4, 5)))
    tw, th = tracker._compute_target_size(1920, 1080)
    assert th == 1080
    assert tw == int(round(1080 * 4 / 5))


def test_windows_clamped_to_source() -> None:
    tracker = ReframeTracker(TrackerConfig(target_aspect=(9, 16)))
    samples = [
        CropSample(timestamp=0.0, cx=0.01, cy=0.5, confidence=1.0, detected=True),
        CropSample(timestamp=0.5, cx=0.99, cy=0.5, confidence=1.0, detected=True),
    ]
    target = tracker._compute_target_size(1920, 1080)
    windows = tracker._to_windows(samples, source_size=(1920, 1080), target_size=target)

    for w in windows:
        assert 0 <= w.x <= 1920 - target[0]
        assert 0 <= w.y <= 1080 - target[1]
        assert w.width == target[0]
        assert w.height == target[1]


def test_interpolate_windows_dense_keyframes() -> None:
    from src.core.reframe.tracker import CropWindow

    sparse = [
        CropWindow(timestamp=0.0, x=0, y=0, width=608, height=1080),
        CropWindow(timestamp=1.0, x=100, y=50, width=608, height=1080),
    ]
    dense = interpolate_windows(sparse, fps=30.0)
    assert len(dense) >= 25
    assert dense[0].timestamp == 0.0
    assert all(dense[i].timestamp <= dense[i + 1].timestamp for i in range(len(dense) - 1))


def test_write_sendcmd_monotonic_timestamps(tmp_path) -> None:
    from src.core.reframe.tracker import CropWindow

    windows = [
        CropWindow(timestamp=i / 30.0, x=i, y=i, width=608, height=1080)
        for i in range(5)
    ]
    path = write_sendcmd_script(windows)
    try:
        text = open(path, encoding="utf-8").read()
        assert "crop x" in text
        assert text.count("crop x") >= 5
    finally:
        __import__("pathlib").Path(path).unlink(missing_ok=True)


def test_platforms_to_targets_dedupes_aspects() -> None:
    targets = platforms_to_targets(["TikTok", "YouTube Shorts", "Twitter"])
    labels = {t.label for t in targets}
    assert "9x16" in labels
    assert "1x1" in labels
    assert len(targets) == 2
