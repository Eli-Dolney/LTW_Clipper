"""Face/subject tracking for smart vertical (and square) reframing.

Approach:
- Decode sequentially and sample every Nth frame for stable timestamps.
- MediaPipe Face Detection is the primary tracker (fast, accurate, local).
- Fallback: OpenCV Haar cascade if MediaPipe fails at runtime.
- Temporal face selection prefers the face nearest the previous center.
- Missed detections hold the last known position (no snap to center).
- Samples are smoothed with velocity-limited EMA + deadzone.
- The renderer interpolates between samples for smooth pans.

Everything here is pure CPU and requires no network access.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger(__name__)


# ---- Data models -----------------------------------------------------------

@dataclass
class TrackerConfig:
    """Tunables for the reframe tracker."""

    target_aspect: tuple[int, int] = (9, 16)
    sample_fps: float = 4.0          # how many samples per second of source
    smoothing: float = 0.35          # EMA factor (0..1). Higher = stickier crop.
    deadzone: float = 0.04           # movement smaller than this (fraction) is ignored
    padding: float = 0.05            # extra margin around the detected subject center
    headroom: float = 0.08           # bias crop upward so heads aren't clipped
    min_confidence: float = 0.35     # MediaPipe / Haar detection threshold
    max_samples: int = 2000          # guardrail for very long sources
    max_pan_speed: float = 0.18      # max normalized center move per second
    recenter_bias: float = 0.02      # gentle pull toward frame center when idle
    zoom: float = 1.0                # >1 zooms in (smaller crop), <1 shows more context


@dataclass
class FaceCandidate:
    """One detected face in normalized coordinates."""

    cx: float
    cy: float
    confidence: float
    area: float = 0.0


@dataclass
class CropSample:
    """One detection sample: normalized (0..1) subject center at a timestamp."""

    timestamp: float
    cx: float = 0.5
    cy: float = 0.5
    confidence: float = 0.0
    detected: bool = False


@dataclass
class CropWindow:
    """A concrete crop rectangle at a specific timestamp.

    Coordinates are in absolute pixels of the source frame.
    """

    timestamp: float
    x: int
    y: int
    width: int
    height: int


@dataclass
class TrackedReframe:
    """Full output of the tracker."""

    source_size: tuple[int, int]       # (width, height)
    target_size: tuple[int, int]       # (width, height) for default aspect
    target_aspect: tuple[int, int] = (9, 16)
    fps: float = 30.0
    samples: list[CropSample] = field(default_factory=list)
    windows: list[CropWindow] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.windows[-1].timestamp if self.windows else 0.0

    def windows_for_aspect(
        self,
        aspect: tuple[int, int],
        *,
        zoom: float = 1.0,
    ) -> list[CropWindow]:
        """Build crop windows for a different target aspect from stored samples."""
        tracker = ReframeTracker(TrackerConfig(target_aspect=aspect, zoom=zoom))
        sw, sh = self.source_size
        target_size = tracker._compute_target_size(sw, sh, zoom=zoom)
        return tracker._to_windows(
            self.samples,
            source_size=self.source_size,
            target_size=target_size,
        )


# ---- Tracker ---------------------------------------------------------------

class ReframeTracker:
    """Produces a smoothed subject-tracked crop path for a video."""

    def __init__(self, config: TrackerConfig | None = None) -> None:
        self.config = config or TrackerConfig()

    # ---- Public API --------------------------------------------------------

    def track(self, source: Path) -> TrackedReframe:
        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise FileNotFoundError(f"Could not open video: {source}")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            if width == 0 or height == 0:
                raise RuntimeError(f"Invalid video dimensions for {source}")

            step = max(1, int(round(fps / self.config.sample_fps)))
            detector = _make_multi_detector(self.config.min_confidence, self.config.headroom)

            raw_samples: list[CropSample] = []
            frame_idx = 0
            prev_cx = 0.5
            prev_cy = 0.5

            while True:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break

                if frame_idx % step == 0:
                    ts = frame_idx / fps
                    faces = detector(frame)
                    if faces:
                        best = _select_face(faces, prev_cx, prev_cy)
                        prev_cx, prev_cy = best.cx, best.cy
                        raw_samples.append(CropSample(
                            timestamp=round(ts, 3),
                            cx=best.cx,
                            cy=best.cy,
                            confidence=best.confidence,
                            detected=True,
                        ))
                    else:
                        # Hold last known position — never snap to center.
                        raw_samples.append(CropSample(
                            timestamp=round(ts, 3),
                            cx=prev_cx,
                            cy=prev_cy,
                            confidence=0.0,
                            detected=False,
                        ))

                    if len(raw_samples) >= self.config.max_samples:
                        break

                frame_idx += 1
        finally:
            cap.release()

        if not raw_samples:
            raw_samples.append(CropSample(timestamp=0.0, cx=0.5, cy=0.5, confidence=0.0, detected=False))

        smoothed = self._smooth_samples(raw_samples)
        target_size = self._compute_target_size(width, height, zoom=self.config.zoom)
        windows = self._to_windows(
            smoothed,
            source_size=(width, height),
            target_size=target_size,
        )

        return TrackedReframe(
            source_size=(width, height),
            target_size=target_size,
            target_aspect=self.config.target_aspect,
            fps=fps,
            samples=smoothed,
            windows=windows,
        )

    # ---- Smoothing ---------------------------------------------------------

    def _smooth_samples(self, samples: list[CropSample]) -> list[CropSample]:
        if not samples:
            return samples

        smoothed: list[CropSample] = []
        prev_cx = samples[0].cx
        prev_cy = samples[0].cy
        prev_ts = samples[0].timestamp
        alpha = max(0.0, min(1.0, self.config.smoothing))
        dead = self.config.deadzone
        max_speed = max(0.01, self.config.max_pan_speed)
        recenter = max(0.0, self.config.recenter_bias)

        for s in samples:
            dt = max(0.001, s.timestamp - prev_ts)
            prev_ts = s.timestamp

            target_cx = s.cx
            target_cy = s.cy

            # Gentle recenter when we haven't seen a face recently.
            if not s.detected and recenter > 0:
                target_cx = target_cx * (1 - recenter) + 0.5 * recenter
                target_cy = target_cy * (1 - recenter) + 0.5 * recenter

            dx = abs(target_cx - prev_cx)
            dy = abs(target_cy - prev_cy)

            if dx < dead:
                target_cx = prev_cx
            if dy < dead:
                target_cy = prev_cy

            # Velocity limit: clamp per-step movement.
            max_step = max_speed * dt
            step_x = float(np.clip(target_cx - prev_cx, -max_step, max_step))
            step_y = float(np.clip(target_cy - prev_cy, -max_step, max_step))
            limited_cx = prev_cx + step_x
            limited_cy = prev_cy + step_y

            new_cx = alpha * prev_cx + (1 - alpha) * limited_cx
            new_cy = alpha * prev_cy + (1 - alpha) * limited_cy

            smoothed.append(CropSample(
                timestamp=s.timestamp,
                cx=float(np.clip(new_cx, 0.0, 1.0)),
                cy=float(np.clip(new_cy, 0.0, 1.0)),
                confidence=s.confidence,
                detected=s.detected,
            ))
            prev_cx, prev_cy = new_cx, new_cy

        return smoothed

    # ---- Geometry ----------------------------------------------------------

    def _compute_target_size(
        self,
        width: int,
        height: int,
        *,
        zoom: float | None = None,
    ) -> tuple[int, int]:
        tw, th = self.config.target_aspect
        zoom = zoom if zoom is not None else self.config.zoom
        zoom = max(0.5, min(2.0, zoom))

        crop_h = height
        crop_w = int(round(height * tw / th))
        if crop_w > width:
            crop_w = width
            crop_h = int(round(width * th / tw))

        if zoom > 1.0:
            crop_w = max(1, int(round(crop_w / zoom)))
            crop_h = max(1, int(round(crop_h / zoom)))

        return crop_w, crop_h

    def _to_windows(
        self,
        samples: list[CropSample],
        *,
        source_size: tuple[int, int],
        target_size: tuple[int, int],
    ) -> list[CropWindow]:
        sw, sh = source_size
        tw, th = target_size
        pad = self.config.padding
        windows: list[CropWindow] = []
        for s in samples:
            abs_cx = s.cx * sw
            abs_cy = s.cy * sh - (pad * sh)  # headroom: shift crop up
            x = int(round(abs_cx - tw / 2))
            y = int(round(abs_cy - th / 2))
            x = max(0, min(sw - tw, x))
            y = max(0, min(sh - th, y))
            windows.append(CropWindow(
                timestamp=s.timestamp,
                x=x,
                y=y,
                width=tw,
                height=th,
            ))
        return windows


# ---- Face selection --------------------------------------------------------

def _select_face(
    faces: list[FaceCandidate],
    prev_cx: float,
    prev_cy: float,
) -> FaceCandidate:
    """Pick the face most likely to be the active speaker/subject."""
    if len(faces) == 1:
        return faces[0]

    def score(f: FaceCandidate) -> float:
        dist = ((f.cx - prev_cx) ** 2 + (f.cy - prev_cy) ** 2) ** 0.5
        proximity = max(0.0, 1.0 - dist * 2.5)
        size = min(1.0, f.area * 8.0)
        return proximity * 0.55 + f.confidence * 0.25 + size * 0.20

    return max(faces, key=score)


# ---- Detector plumbing -----------------------------------------------------

def _make_multi_detector(min_conf: float, headroom: float):
    """Return a callable(frame) -> list[FaceCandidate]."""
    try:
        import mediapipe as mp  # type: ignore

        detector = mp.solutions.face_detection.FaceDetection(
            model_selection=1,
            min_detection_confidence=min_conf,
        )

        def _detect(frame: "np.ndarray") -> list[FaceCandidate]:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame.shape[:2]
            result = detector.process(rgb)
            if not result.detections:
                return []
            out: list[FaceCandidate] = []
            for det in result.detections:
                rb = det.location_data.relative_bounding_box
                cx = rb.xmin + rb.width / 2
                cy = rb.ymin + rb.height / 2
                cy = min(1.0, max(0.0, cy - headroom))
                conf = float(det.score[0]) if det.score else 0.0
                area = float(rb.width * rb.height)
                if conf >= min_conf:
                    out.append(FaceCandidate(cx=float(cx), cy=float(cy), confidence=conf, area=area))
            return out

        return _detect

    except Exception as exc:
        log.warning("MediaPipe unavailable (%s); falling back to OpenCV Haar.", exc)
        return _haar_multi_detector(min_conf, headroom)


def _haar_multi_detector(min_conf: float, headroom: float):
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)

    def _detect(frame: "np.ndarray") -> list[FaceCandidate]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = frame.shape[:2]
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48))
        if len(faces) == 0:
            return []
        out: list[FaceCandidate] = []
        for x, y, fw, fh in faces:
            cx = (x + fw / 2) / w
            cy = (y + fh / 2) / h
            cy = min(1.0, max(0.0, cy - headroom))
            conf = min(1.0, (fw * fh) / (w * h) * 6.0)
            conf = max(min_conf, conf)
            out.append(FaceCandidate(
                cx=float(cx), cy=float(cy), confidence=float(conf),
                area=float((fw * fh) / (w * h)),
            ))
        return out

    return _detect
