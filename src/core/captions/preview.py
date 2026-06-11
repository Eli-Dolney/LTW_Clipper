"""Generate live caption-style preview images for the Text Studio GUI."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from .burner import _escape_ffmpeg_path
from .models import CaptionStyleModel, TextOverlayModel
from .styler import CaptionStyler

log = logging.getLogger(__name__)


def _sample_frame_path() -> Path:
    return Path(__file__).resolve().parents[3] / "assets" / "preview" / "sample_frame.jpg"


def ensure_sample_frame(ffmpeg_binary: str = "ffmpeg") -> Path:
    """Create a 9:16 sample frame if it does not exist."""
    path = _sample_frame_path()
    if path.is_file():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_binary, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi",
        "-i", "color=c=0x1a1a2e:s=1080x1920:d=1",
        "-frames:v", "1",
        str(path),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        log.warning("Could not generate sample frame via ffmpeg: %s", exc)
        # Pillow fallback
        try:
            from PIL import Image, ImageDraw

            img = Image.new("RGB", (1080, 1920), color=(26, 26, 46))
            draw = ImageDraw.Draw(img)
            draw.rectangle((80, 400, 1000, 1520), outline=(60, 60, 90), width=4)
            img.save(path, "JPEG", quality=90)
        except Exception as pil_exc:  # noqa: BLE001
            raise RuntimeError("Could not create preview sample frame") from pil_exc
    return path


def render_style_preview(
    style: CaptionStyleModel,
    output: Path,
    *,
    sample_text: str = "This is how your captions look",
    overlays: list[TextOverlayModel] | None = None,
    overlay_metadata: dict[str, str] | None = None,
    duration: float = 3.0,
    ffmpeg_binary: str = "ffmpeg",
) -> Path:
    """Burn a sample ASS caption onto the sample frame and write a JPEG."""
    frame = ensure_sample_frame(ffmpeg_binary)
    output.parent.mkdir(parents=True, exist_ok=True)

    styler = CaptionStyler(style)
    ass_content = styler.build_preview_ass(
        sample_text=sample_text,
        overlays=overlays,
        overlay_metadata=overlay_metadata,
        duration=duration,
    )

    with tempfile.TemporaryDirectory() as tmp:
        ass_path = Path(tmp) / "preview.ass"
        ass_path.write_text(ass_content, encoding="utf-8")
        ass_escaped = _escape_ffmpeg_path(ass_path)
        cmd = [
            ffmpeg_binary, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(frame),
            "-vf", f"ass={ass_escaped}",
            "-frames:v", "1",
            str(output),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output
