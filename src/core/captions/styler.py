"""Convert Whisper word timestamps into stylized ASS/SRT/VTT captions.

The ASS output supports per-word karaoke-style highlighting (pop-in + color
shift on the active word), opacity, fade animations, and standalone text overlays.
SRT and VTT outputs are produced from the same segments for upload to YouTube / TikTok.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models import Transcript, TranscriptSegment, WordTiming
from .models import CaptionStyleModel, TextOverlayModel, resolve_overlay_tokens

# Backward-compatible alias
CaptionStyle = CaptionStyleModel


# ---- Built-in presets (fallback when JSON styles are unavailable) -----------

CAPTION_PRESETS: dict[str, CaptionStyleModel] = {
    "bold_outline": CaptionStyleModel(
        name="bold_outline",
        font="Arial Black",
        font_size=64,
        primary_rgb=(255, 255, 255),
        highlight_rgb=(255, 214, 10),
        outline_px=6,
        uppercase=True,
        builtin=True,
    ),
    "minimal": CaptionStyleModel(
        name="minimal",
        font="Helvetica",
        font_size=52,
        primary_rgb=(255, 255, 255),
        highlight_rgb=(200, 220, 255),
        outline_px=3,
        uppercase=False,
        bold=False,
        builtin=True,
    ),
    "mrbeast": CaptionStyleModel(
        name="mrbeast",
        font="Impact",
        font_size=72,
        primary_rgb=(255, 255, 255),
        highlight_rgb=(255, 80, 80),
        outline_px=8,
        uppercase=True,
        highlight_pop=True,
        highlight_scale=125,
        builtin=True,
    ),
    "tiktok": CaptionStyleModel(
        name="tiktok",
        font="Montserrat",
        font_size=58,
        primary_rgb=(255, 255, 255),
        highlight_rgb=(0, 220, 255),
        outline_px=4,
        border_style=1,
        uppercase=False,
        builtin=True,
    ),
    "hormozi": CaptionStyleModel(
        name="hormozi",
        font="Arial Black",
        font_size=68,
        primary_rgb=(255, 255, 255),
        highlight_rgb=(255, 220, 0),
        outline_px=7,
        uppercase=True,
        highlight_pop=True,
        highlight_scale=120,
        alignment=2,
        margin_v=200,
        builtin=True,
    ),
    "clean_box": CaptionStyleModel(
        name="clean_box",
        font="Helvetica",
        font_size=54,
        primary_rgb=(255, 255, 255),
        highlight_rgb=(255, 255, 255),
        outline_px=0,
        border_style=3,
        back_rgb=(0, 0, 0),
        back_opacity=55,
        uppercase=False,
        bold=False,
        builtin=True,
    ),
    "neon": CaptionStyleModel(
        name="neon",
        font="Arial Black",
        font_size=60,
        primary_rgb=(0, 255, 255),
        highlight_rgb=(255, 0, 255),
        outline_rgb=(0, 80, 160),
        outline_px=5,
        shadow_px=2,
        uppercase=True,
        builtin=True,
    ),
    "subtle_lower": CaptionStyleModel(
        name="subtle_lower",
        font="Helvetica",
        font_size=44,
        primary_rgb=(240, 240, 240),
        highlight_rgb=(255, 255, 255),
        outline_px=2,
        primary_opacity=85,
        uppercase=False,
        bold=False,
        alignment=2,
        margin_v=120,
        fade_in_ms=200,
        fade_out_ms=200,
        builtin=True,
    ),
}


# ---- Styler ----------------------------------------------------------------

@dataclass
class CaptionArtifacts:
    """Paths to the files emitted by :meth:`CaptionStyler.write`."""

    ass: Path | None = None
    srt: Path | None = None
    vtt: Path | None = None


class CaptionStyler:
    """Produce ASS/SRT/VTT captions from a :class:`Transcript`.

    The transcript is assumed to carry word-level timestamps (Whisper does
    this when called with ``word_timestamps=True``). If words are missing,
    the styler falls back to per-segment subtitles without karaoke.
    """

    def __init__(
        self,
        style: CaptionStyleModel | str = "bold_outline",
        *,
        video_size: tuple[int, int] = (1080, 1920),
    ) -> None:
        if isinstance(style, str):
            self.style = _resolve_style(style)
        else:
            self.style = style
        self.video_size = video_size

    # ---- Public API --------------------------------------------------------

    def write(
        self,
        transcript: Transcript,
        out_dir: Path,
        *,
        base_name: str = "captions",
        clip_offset: float = 0.0,
        clip_end: float | None = None,
        formats: tuple[str, ...] = ("ass", "srt", "vtt"),
        overlays: list[TextOverlayModel] | None = None,
        overlay_metadata: dict[str, str] | None = None,
        clip_duration: float | None = None,
    ) -> CaptionArtifacts:
        """Write caption files and return their paths.

        ``clip_offset`` shifts every timestamp so you can feed a full-length
        transcript and emit captions for just one clip window.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        artifacts = CaptionArtifacts()

        filtered = self._filter_segments(transcript, clip_offset, clip_end)
        duration = clip_duration
        if duration is None and filtered:
            duration = max(seg.end for seg in filtered)
        elif duration is None:
            duration = 0.0

        if "ass" in formats:
            ass_path = out_dir / f"{base_name}.ass"
            ass_path.write_text(
                self._build_ass(
                    filtered,
                    overlays=overlays or [],
                    overlay_metadata=overlay_metadata,
                    clip_duration=duration,
                ),
                encoding="utf-8",
            )
            artifacts.ass = ass_path
        if "srt" in formats:
            srt_path = out_dir / f"{base_name}.srt"
            srt_path.write_text(self._build_srt(filtered), encoding="utf-8")
            artifacts.srt = srt_path
        if "vtt" in formats:
            vtt_path = out_dir / f"{base_name}.vtt"
            vtt_path.write_text(self._build_vtt(filtered), encoding="utf-8")
            artifacts.vtt = vtt_path

        return artifacts

    def build_preview_ass(
        self,
        *,
        sample_text: str = "This is how your captions look",
        overlays: list[TextOverlayModel] | None = None,
        overlay_metadata: dict[str, str] | None = None,
        duration: float = 3.0,
    ) -> str:
        """Build ASS for a static preview (no transcript required)."""
        words = sample_text.split()
        if not words:
            words = ["Preview"]
        step = duration / max(len(words), 1)
        word_timings = [
            WordTiming(word=w, start=i * step, end=(i + 1) * step, probability=1.0)
            for i, w in enumerate(words)
        ]
        seg = TranscriptSegment(
            id=0,
            start=0.0,
            end=duration,
            text=sample_text,
            words=word_timings,
        )
        return self._build_ass(
            [seg],
            overlays=overlays or [],
            overlay_metadata=overlay_metadata,
            clip_duration=duration,
        )

    # ---- Filtering ---------------------------------------------------------

    def _filter_segments(
        self,
        transcript: Transcript,
        offset: float,
        end: float | None,
    ) -> list[TranscriptSegment]:
        out: list[TranscriptSegment] = []
        for seg in transcript.segments:
            if end is not None and seg.start >= end:
                continue
            if seg.end <= offset:
                continue
            new_start = max(0.0, seg.start - offset)
            new_end = (seg.end - offset) if end is None else min(seg.end, end) - offset
            if new_end <= new_start:
                continue
            new_words: list[WordTiming] = []
            for w in seg.words:
                if end is not None and w.start >= end:
                    continue
                if w.end <= offset:
                    continue
                new_words.append(WordTiming(
                    word=w.word,
                    start=max(0.0, w.start - offset),
                    end=(w.end - offset) if end is None else min(w.end, end) - offset,
                    probability=w.probability,
                ))
            out.append(TranscriptSegment(
                id=seg.id,
                start=new_start,
                end=new_end,
                text=seg.text,
                words=new_words,
            ))
        return out

    # ---- ASS builder -------------------------------------------------------

    def _build_ass(
        self,
        segments: list[TranscriptSegment],
        *,
        overlays: list[TextOverlayModel],
        overlay_metadata: dict[str, str] | None,
        clip_duration: float,
    ) -> str:
        style = self.style
        w, h = self.video_size
        header = self._ass_header(style, w, h)
        overlay_styles = self._overlay_style_lines(overlays)
        lines = [header, *overlay_styles, "[Events]\n",
                 "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"]

        highlight_bgr = _rgb_to_ass_bgr(
            style.highlight_rgb, style.highlight_opacity,
        )

        for seg in segments:
            line_events = _split_into_lines(
                seg,
                max_chars=style.max_chars_per_line,
                max_words=style.max_words_per_line,
                uppercase=style.uppercase,
                highlight=highlight_bgr,
                highlight_pop=style.highlight_pop,
                highlight_scale=style.highlight_scale,
            )
            for start, end, text in line_events:
                prefix = _fade_prefix(style.fade_in_ms, style.fade_out_ms)
                lines.append(
                    f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,"
                    f"{prefix}{text}\n"
                )

        for idx, overlay in enumerate(overlays):
            start = overlay.start if overlay.start is not None else 0.0
            end = overlay.end if overlay.end is not None else max(clip_duration, start + 1.0)
            if end <= start:
                end = start + 1.0
            text = resolve_overlay_tokens(overlay.text, overlay_metadata)
            if overlay.uppercase:
                text = text.upper()
            prefix = _fade_prefix(overlay.fade_in_ms, overlay.fade_out_ms)
            style_name = f"Overlay{idx}"
            lines.append(
                f"Dialogue: 1,{_ass_time(start)},{_ass_time(end)},{style_name},,0,0,0,,"
                f"{prefix}{_ass_escape(text)}\n"
            )

        return "".join(lines)

    def _ass_header(self, style: CaptionStyleModel, w: int, h: int) -> str:
        primary = _rgb_to_ass_bgr(style.primary_rgb, style.primary_opacity)
        outline = _rgb_to_ass_bgr(style.outline_rgb, style.outline_opacity)
        back = _rgb_to_ass_bgr(style.back_rgb, style.back_opacity)
        highlight = _rgb_to_ass_bgr(style.highlight_rgb, style.highlight_opacity)
        bold = -1 if style.bold else 0
        italic = -1 if style.italic else 0
        margin_v = style.margin_v if style.margin_v else style.bottom_margin_px

        return (
            "[Script Info]\n"
            "; Generated by LTW Video Splitter Pro\n"
            "ScriptType: v4.00+\n"
            "Collisions: Normal\n"
            "WrapStyle: 0\n"
            f"PlayResX: {w}\n"
            f"PlayResY: {h}\n"
            "ScaledBorderAndShadow: yes\n"
            "\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Default,{style.font},{style.font_size},{primary},"
            f"{highlight},{outline},{back},{bold},{italic},0,0,100,100,0,0,"
            f"{style.border_style},{style.outline_px},{style.shadow_px},"
            f"{style.alignment},{style.margin_h},{style.margin_h},{margin_v},1\n"
            "\n"
        )

    def _overlay_style_lines(self, overlays: list[TextOverlayModel]) -> list[str]:
        lines: list[str] = []
        base = self.style
        for idx, overlay in enumerate(overlays):
            font = overlay.font or base.font
            size = overlay.font_size or max(base.font_size, 48)
            primary_rgb = overlay.primary_rgb or base.primary_rgb
            outline_rgb = overlay.outline_rgb or base.outline_rgb
            back_rgb = overlay.back_rgb or base.back_rgb
            primary = _rgb_to_ass_bgr(primary_rgb, overlay.primary_opacity)
            outline = _rgb_to_ass_bgr(outline_rgb, overlay.outline_opacity)
            back = _rgb_to_ass_bgr(back_rgb, overlay.back_opacity)
            highlight = primary
            bold = -1 if overlay.bold else 0
            italic = -1 if overlay.italic else 0
            style_name = f"Overlay{idx}"
            lines.append(
                f"Style: {style_name},{font},{size},{primary},"
                f"{highlight},{outline},{back},{bold},{italic},0,0,100,100,0,0,"
                f"{overlay.border_style},{overlay.outline_px},{overlay.shadow_px},"
                f"{overlay.alignment},{overlay.margin_h},{overlay.margin_h},"
                f"{overlay.margin_v},1\n"
            )
        return lines

    # ---- SRT / VTT ---------------------------------------------------------

    def _build_srt(self, segments: list[TranscriptSegment]) -> str:
        lines: list[str] = []
        for i, seg in enumerate(segments, start=1):
            lines.append(str(i))
            lines.append(f"{_srt_time(seg.start)} --> {_srt_time(seg.end)}")
            lines.append(_wrap_text(seg.text, max_chars=self.style.max_chars_per_line * 2))
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    def _build_vtt(self, segments: list[TranscriptSegment]) -> str:
        lines = ["WEBVTT", ""]
        for seg in segments:
            lines.append(f"{_vtt_time(seg.start)} --> {_vtt_time(seg.end)}")
            lines.append(_wrap_text(seg.text, max_chars=self.style.max_chars_per_line * 2))
            lines.append("")
        return "\n".join(lines).strip() + "\n"


# ---- Style resolution ------------------------------------------------------

def _resolve_style(name: str) -> CaptionStyleModel:
    """Resolve a style name from StyleManager or built-in presets."""
    try:
        from .style_manager import StyleManager

        mgr = StyleManager()
        style = mgr.get(name)
        if style is not None:
            return style
    except Exception:  # noqa: BLE001
        pass
    if name in CAPTION_PRESETS:
        return CAPTION_PRESETS[name]
    raise ValueError(f"Unknown caption style: {name}")


# ---- Helpers ---------------------------------------------------------------

def _opacity_to_ass_alpha(opacity: int) -> int:
    """Map 0-100 opacity (100=opaque) to ASS alpha byte (00=opaque)."""
    clamped = max(0, min(100, opacity))
    return int(round((100 - clamped) * 255 / 100))


def _rgb_to_ass_bgr(rgb: tuple[int, int, int], opacity: int = 100) -> str:
    r, g, b = rgb
    alpha = _opacity_to_ass_alpha(opacity)
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def _fade_prefix(fade_in_ms: int, fade_out_ms: int) -> str:
    if fade_in_ms <= 0 and fade_out_ms <= 0:
        return ""
    return f"{{\\fad({fade_in_ms},{fade_out_ms})}}"


def _ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _srt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    ms_total = int(round(seconds * 1000))
    h, rem = divmod(ms_total, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _vtt_time(seconds: float) -> str:
    return _srt_time(seconds).replace(",", ".")


def _wrap_text(text: str, *, max_chars: int) -> str:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    length = 0
    for w in words:
        if length + len(w) + 1 > max_chars and current:
            lines.append(" ".join(current))
            current, length = [w], len(w)
        else:
            current.append(w)
            length += len(w) + 1
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def _split_into_lines(
    seg: TranscriptSegment,
    *,
    max_chars: int,
    max_words: int,
    uppercase: bool,
    highlight: str,
    highlight_pop: bool,
    highlight_scale: int,
) -> list[tuple[float, float, str]]:
    """Build one or more ASS events for a single transcript segment."""
    if not seg.words:
        text = seg.text.upper() if uppercase else seg.text
        return [(seg.start, seg.end, text)]

    lines: list[list[WordTiming]] = []
    current: list[WordTiming] = []
    current_chars = 0
    for w in seg.words:
        word_text = w.word.strip()
        if not word_text:
            continue
        if (
            (len(current) + 1 > max_words or current_chars + len(word_text) + 1 > max_chars)
            and current
        ):
            lines.append(current)
            current, current_chars = [], 0
        current.append(w)
        current_chars += len(word_text) + 1
    if current:
        lines.append(current)

    out: list[tuple[float, float, str]] = []
    for chunk in lines:
        if not chunk:
            continue
        line_start = chunk[0].start
        line_end = chunk[-1].end
        pieces: list[str] = []
        for w in chunk:
            raw = w.word.strip()
            if uppercase:
                raw = raw.upper()
            dur_cs = max(1, int(round((w.end - w.start) * 100)))
            escaped = _ass_escape(raw)
            if highlight_pop and highlight_scale > 100:
                pop_tag = (
                    f"{{\\t(0,{dur_cs * 10},\\fscx{highlight_scale}\\fscy{highlight_scale})}}"
                )
                pieces.append(f"{{\\k{dur_cs}}}{pop_tag}{escaped} ")
            else:
                pieces.append(f"{{\\k{dur_cs}}}{escaped} ")
        text = "".join(pieces).rstrip()
        out.append((line_start, line_end, text))
    return out


def _ass_escape(text: str) -> str:
    return text.replace("{", "\\{").replace("}", "\\}").replace("\\N", " ")
