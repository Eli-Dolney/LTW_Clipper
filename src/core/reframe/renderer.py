"""Render a vertically reframed video driven by a tracked crop time-series.

Uses ffmpeg's ``sendcmd``/``crop`` filter combo for smooth per-frame moves.
Supports crop / fit / blur layout modes and true platform resolutions.

All rendering is local - no cloud, no API keys.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .platform_specs import ReframeTarget, default_targets
from .tracker import CropWindow, ReframeTracker, TrackerConfig, TrackedReframe

log = logging.getLogger(__name__)

LayoutMode = Literal["crop", "fit", "blur"]


@dataclass
class RenderConfig:
    """Options passed to each reframe render."""

    layout: LayoutMode = "crop"
    output_resolution: tuple[int, int] | None = None  # (width, height)
    zoom: float = 1.0
    preview: bool = False
    preview_duration: float = 5.0
    crf: int = 20
    preset: str = "medium"


class ReframeRenderer:
    """Render a reframed copy of ``source`` using the tracker + ffmpeg."""

    def __init__(
        self,
        *,
        ffmpeg_binary: str = "ffmpeg",
        tracker_config: TrackerConfig | None = None,
        render_config: RenderConfig | None = None,
    ) -> None:
        self.ffmpeg = ffmpeg_binary
        self.tracker = ReframeTracker(tracker_config)
        self.render_config = render_config or RenderConfig()
        self._tracker_config = tracker_config or TrackerConfig()

    # ---- Public API --------------------------------------------------------

    def track(self, source: Path) -> TrackedReframe:
        return self.tracker.track(source)

    def render(
        self,
        source: Path,
        output: Path,
        *,
        reframe: TrackedReframe | None = None,
        target_aspect: tuple[int, int] | None = None,
        layout: LayoutMode | None = None,
        output_resolution: tuple[int, int] | None = None,
        crf: int | None = None,
        preset: str | None = None,
        preview: bool = False,
    ) -> Path:
        if reframe is None:
            reframe = self.tracker.track(source)

        cfg = self.render_config
        layout = layout or cfg.layout
        crf = crf if crf is not None else cfg.crf
        preset = preset or cfg.preset
        if preview:
            preset = "ultrafast"
            crf = min(crf + 6, 35)

        aspect = target_aspect or reframe.target_aspect
        out_w, out_h = output_resolution or cfg.output_resolution or _default_resolution(aspect)

        if aspect != reframe.target_aspect:
            windows = reframe.windows_for_aspect(aspect, zoom=self._tracker_config.zoom)
            tw, th = ReframeTracker(
                TrackerConfig(target_aspect=aspect, zoom=self._tracker_config.zoom)
            )._compute_target_size(*reframe.source_size)
        else:
            windows = reframe.windows
            tw, th = reframe.target_size

        output.parent.mkdir(parents=True, exist_ok=True)

        if layout == "fit":
            return self._render_fit(source, output, out_w, out_h, crf=crf, preset=preset, preview=preview)
        if layout == "blur":
            return self._render_blur(
                source, output, windows, tw, th, out_w, out_h,
                reframe.fps, crf=crf, preset=preset, preview=preview,
            )
        return self._render_crop(
            source, output, windows, tw, th, out_w, out_h,
            reframe.fps, crf=crf, preset=preset, preview=preview,
        )

    def render_all(
        self,
        source: Path,
        output_dir: Path,
        *,
        reframe: TrackedReframe | None = None,
        targets: list[ReframeTarget] | None = None,
        layout: LayoutMode | None = None,
        crf: int | None = None,
        preset: str | None = None,
    ) -> dict[str, Path]:
        """Render one file per target aspect from a single tracked path."""
        if reframe is None:
            reframe = self.track(source)

        targets = targets or default_targets()
        outputs: dict[str, Path] = {}
        for target in targets:
            label = target.label
            out_path = output_dir / f"clip_{label}.mp4"
            self.render(
                source,
                out_path,
                reframe=reframe,
                target_aspect=target.aspect,
                layout=layout,
                output_resolution=target.resolution,
                crf=crf,
                preset=preset,
            )
            outputs[label] = out_path
        return outputs

    # ---- Layout: crop (tracked) --------------------------------------------

    def _render_crop(
        self,
        source: Path,
        output: Path,
        windows: list[CropWindow],
        tw: int,
        th: int,
        out_w: int,
        out_h: int,
        fps: float,
        *,
        crf: int,
        preset: str,
        preview: bool,
    ) -> Path:
        dense = interpolate_windows(windows, fps=fps)
        cmd_file = write_sendcmd_script(dense)

        scale = f",scale={out_w}:{out_h}:flags=lanczos" if (out_w, out_h) != (tw, th) else ""
        filter_graph = (
            f"sendcmd=f='{cmd_file}',"
            f"crop=w={tw}:h={th}:x=0:y=0:exact=1"
            f"{scale}"
        )

        cmd = self._base_cmd(source, output, filter_graph, crf, preset, preview)
        try:
            self._run(cmd)
        finally:
            Path(cmd_file).unlink(missing_ok=True)
        return output

    # ---- Layout: fit (letterbox, nothing cut off) ----------------------------

    def _render_fit(
        self,
        source: Path,
        output: Path,
        out_w: int,
        out_h: int,
        *,
        crf: int,
        preset: str,
        preview: bool,
    ) -> Path:
        vf = (
            f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
            f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:black"
        )
        cmd = self._base_cmd(source, output, vf, crf, preset, preview)
        self._run(cmd)
        return output

    # ---- Layout: blur (blurred bg + tracked foreground) --------------------

    def _render_blur(
        self,
        source: Path,
        output: Path,
        windows: list[CropWindow],
        tw: int,
        th: int,
        out_w: int,
        out_h: int,
        fps: float,
        *,
        crf: int,
        preset: str,
        preview: bool,
    ) -> Path:
        dense = interpolate_windows(windows, fps=fps)
        cmd_file = write_sendcmd_script(dense)

        # Background: full frame scaled+blurred to fill output.
        # Foreground: tracked crop scaled to ~85% width, centered vertically upper-third.
        fg_h = int(out_h * 0.55)
        fg_w = int(out_w * 0.92)
        filter_graph = (
            f"split[bg][fg];"
            f"[bg]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h},boxblur=20:5[blurred];"
            f"[fg]sendcmd=f='{cmd_file}',crop=w={tw}:h={th}:x=0:y=0:exact=1,"
            f"scale={fg_w}:{fg_h}:flags=lanczos[tracked];"
            f"[blurred][tracked]overlay=(W-w)/2:(H-h)/3"
        )
        cmd = self._base_cmd(source, output, filter_graph, crf, preset, preview)
        try:
            self._run(cmd)
        finally:
            Path(cmd_file).unlink(missing_ok=True)
        return output

    # ---- Center-crop fallback (no tracking) --------------------------------

    def render_center(
        self,
        source: Path,
        output: Path,
        *,
        target_aspect: tuple[int, int] = (9, 16),
        output_resolution: tuple[int, int] | None = None,
        crf: int = 20,
        preset: str = "medium",
    ) -> Path:
        """Classic center-crop: no tracking, used as fallback."""
        aw, ah = target_aspect
        out_w, out_h = output_resolution or _default_resolution(target_aspect)
        vf = (
            f"crop=w='if(gt(a,{aw}/{ah}),ih*{aw}/{ah},iw)':"
            f"h='if(gt(a,{aw}/{ah}),ih,iw*{ah}/{aw})',"
            f"scale={out_w}:{out_h}:flags=lanczos"
        )
        cmd = self._base_cmd(source, output, vf, crf, preset, preview=False)
        self._run(cmd)
        return output

    # ---- Preview overlay (static frame) ------------------------------------

    def preview_overlay(
        self,
        source: Path,
        output_image: Path,
        *,
        reframe: TrackedReframe | None = None,
        target_aspect: tuple[int, int] = (9, 16),
        layout: LayoutMode = "crop",
        timestamp: float = 1.0,
    ) -> Path:
        """Draw crop box / layout guide on a single frame for GUI preview."""
        import cv2
        import numpy as np

        if reframe is None:
            reframe = self.track(source)

        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise FileNotFoundError(source)
        try:
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ok, frame = cap.read()
            if not ok or frame is None:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = cap.read()
            if not ok or frame is None:
                raise RuntimeError("Could not read preview frame")
        finally:
            cap.release()

        sw, sh = reframe.source_size
        out_w, out_h = _default_resolution(target_aspect)
        canvas = np.zeros((out_h, out_w, 3), dtype=np.uint8)

        if layout == "fit":
            scale = min(out_w / sw, out_h / sh)
            nw, nh = int(sw * scale), int(sh * scale)
            resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
            x0 = (out_w - nw) // 2
            y0 = (out_h - nh) // 2
            canvas[y0:y0 + nh, x0:x0 + nw] = resized
            cv2.rectangle(canvas, (x0, y0), (x0 + nw, y0 + nh), (0, 220, 255), 2)
        elif layout == "blur":
            bg = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)
            bg = cv2.GaussianBlur(bg, (51, 51), 0)
            canvas = bg.copy()
            windows = reframe.windows_for_aspect(target_aspect)
            win = _window_at_time(windows, timestamp)
            if win:
                crop = frame[win.y:win.y + win.height, win.x:win.x + win.width]
                fg_w, fg_h = int(out_w * 0.92), int(out_h * 0.55)
                fg = cv2.resize(crop, (fg_w, fg_h), interpolation=cv2.INTER_AREA)
                x0 = (out_w - fg_w) // 2
                y0 = out_h // 3
                canvas[y0:y0 + fg_h, x0:x0 + fg_w] = fg
                cv2.rectangle(canvas, (x0, y0), (x0 + fg_w, y0 + fg_h), (0, 255, 120), 2)
        else:
            windows = reframe.windows_for_aspect(target_aspect)
            win = _window_at_time(windows, timestamp)
            if win:
                crop = frame[win.y:win.y + win.height, win.x:win.x + win.width]
                canvas = cv2.resize(crop, (out_w, out_h), interpolation=cv2.INTER_AREA)
                # Draw source crop box on a dimmed full frame inset
                thumb = cv2.resize(frame, (out_w // 4, out_h // 4))
                canvas[10:10 + thumb.shape[0], 10:10 + thumb.shape[1]] = thumb
                sx = int(10 + (win.x / sw) * thumb.shape[1])
                sy = int(10 + (win.y / sh) * thumb.shape[0])
                sw_box = max(1, int((win.width / sw) * thumb.shape[1]))
                sh_box = max(1, int((win.height / sh) * thumb.shape[0]))
                overlay = canvas.copy()
                cv2.rectangle(overlay, (10, 10), (10 + thumb.shape[1], 10 + thumb.shape[0]), (40, 40, 40), -1)
                cv2.addWeighted(overlay, 0.3, canvas, 0.7, 0, canvas)
                canvas[10:10 + thumb.shape[0], 10:10 + thumb.shape[1]] = thumb
                cv2.rectangle(canvas, (sx, sy), (sx + sw_box, sy + sh_box), (0, 255, 120), 2)

        output_image.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_image), canvas)
        return output_image

    def render_preview_clip(
        self,
        source: Path,
        output: Path,
        *,
        target_aspect: tuple[int, int] = (9, 16),
        layout: LayoutMode = "crop",
        duration: float = 5.0,
    ) -> Path:
        """Fast low-res preview of first N seconds."""
        reframe = self.track(source)
        tmp = output.parent / f"_preview_cut_{output.stem}.mp4"
        cmd = [
            self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-t", str(duration),
            "-i", str(source),
            "-c", "copy",
            str(tmp),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            tmp = source

        try:
            return self.render(
                tmp,
                output,
                reframe=reframe,
                target_aspect=target_aspect,
                layout=layout,
                output_resolution=(540, int(540 * target_aspect[1] / target_aspect[0])),
                preview=True,
            )
        finally:
            if tmp != source and tmp.exists():
                tmp.unlink(missing_ok=True)

    # ---- Helpers -----------------------------------------------------------

    def _base_cmd(
        self,
        source: Path,
        output: Path,
        vf: str,
        crf: int,
        preset: str,
        preview: bool,
    ) -> list[str]:
        cmd = [
            self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(source),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k" if preview else "160k",
        ]
        if preview:
            cmd = [
                self.ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-t", str(self.render_config.preview_duration),
                "-i", str(source),
                "-vf", vf,
                "-c:v", "libx264",
                "-preset", preset,
                "-crf", str(crf),
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
            ]
        cmd.append(str(output))
        return cmd

    def _run(self, cmd: list[str]) -> None:
        log.info("ffmpeg reframe: %s", " ".join(cmd[:8]))
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
            raise RuntimeError(f"ffmpeg reframe failed: {stderr[:500]}") from exc


# ---- Interpolation utilities (exported for tests) --------------------------

def interpolate_windows(
    windows: list[CropWindow],
    *,
    fps: float = 30.0,
) -> list[CropWindow]:
    """Densify sparse tracker windows to ~one keyframe per output frame."""
    if not windows:
        return windows
    if len(windows) == 1:
        return windows

    duration = windows[-1].timestamp
    if duration <= 0:
        return windows

    frame_interval = 1.0 / max(1.0, fps)
    dense: list[CropWindow] = []
    t = 0.0
    while t <= duration + 1e-6:
        win = _window_at_time(windows, t)
        if win:
            dense.append(CropWindow(
                timestamp=round(t, 4),
                x=win.x,
                y=win.y,
                width=win.width,
                height=win.height,
            ))
        t += frame_interval

    if dense and dense[-1].timestamp < windows[-1].timestamp:
        dense.append(windows[-1])
    return dense


def write_sendcmd_script(windows: list[CropWindow]) -> str:
    """Emit an ffmpeg ``sendcmd`` script animating the ``crop`` filter x/y."""
    fd, path = tempfile.mkstemp(prefix="ltw_reframe_", suffix=".txt")
    with open(fd, "w", encoding="utf-8") as fh:
        if windows:
            first = windows[0]
            fh.write(f"0 crop x {first.x}, crop y {first.y};\n")
        for win in windows[1:]:
            fh.write(f"{win.timestamp:.4f} crop x {win.x}, crop y {win.y};\n")
    return path


def _window_at_time(windows: list[CropWindow], t: float) -> CropWindow | None:
    if not windows:
        return None
    if t <= windows[0].timestamp:
        return windows[0]
    for i in range(1, len(windows)):
        prev, curr = windows[i - 1], windows[i]
        if t <= curr.timestamp:
            span = curr.timestamp - prev.timestamp
            if span <= 0:
                return curr
            frac = (t - prev.timestamp) / span
            return CropWindow(
                timestamp=t,
                x=int(round(prev.x + (curr.x - prev.x) * frac)),
                y=int(round(prev.y + (curr.y - prev.y) * frac)),
                width=curr.width,
                height=curr.height,
            )
    return windows[-1]


def _default_resolution(aspect: tuple[int, int]) -> tuple[int, int]:
    from .platform_specs import ASPECT_RESOLUTIONS
    return ASPECT_RESOLUTIONS.get(aspect, (1080, int(1080 * aspect[1] / aspect[0])))


# ---- CLI convenience -------------------------------------------------------

def reframe_cli(source: Path, output: Path, mode: str = "smart") -> Path:
    """Minimal helper for ad-hoc use from other modules or the CLI."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH - please install ffmpeg")

    renderer = ReframeRenderer()
    if mode == "center":
        return renderer.render_center(source, output)
    return renderer.render(source, output)
