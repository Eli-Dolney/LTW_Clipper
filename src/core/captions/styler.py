"""Convert Whisper word timestamps into stylized ASS/SRT/VTT captions.

The ASS output supports per-word karaoke-style highlighting (pop-in + color
shift on the active word). SRT and VTT outputs are produced from the same
segments for upload to YouTube / TikTok.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..models import Transcript, TranscriptSegment, WordTiming


# ---- Preset styles ---------------------------------------------------------

@dataclass
class CaptionStyle:
    """ASS style parameters. Colors use RGB, not BGR - we convert internally."""

    name: str = "bold_outline"
    font: str = "Arial Black"
    font_size: int = 64
    primary_rgb: tuple[int, int, int] = (255, 255, 255)
    highlight_rgb: tuple[int, int, int] = (255, 214, 10)   # used for active word
    outline_rgb: tuple[int, int, int] = (0, 0, 0)
    back_rgb: tuple[int, int, int] = (0, 0, 0)
    outline_px: int = 6
    shadow_px: int = 0
    bold: bool = True
    italic: bool = False
    uppercase: bool = True
    max_chars_per_line: int = 22
    max_words_per_line: int = 6
    bottom_margin_px: int = 220
    border_style: int = 1  # 1 = outline+shadow, 3 = opaque box


CAPTION_PRESETS: dict[str, CaptionStyle] = {
    "bold_outline": CaptionStyle(
        name="bold_outline",
        font="Arial Black",
        font_size=64,
        primary_rgb=(255, 255, 255),
        highlight_rgb=(255, 214, 10),
        outline_px=6,
        uppercase=True,
    ),
    "minimal": CaptionStyle(
        name="minimal",
        font="Helvetica",
        font_size=52,
        primary_rgb=(255, 255, 255),
        highlight_rgb=(200, 220, 255),
        outline_px=3,
        uppercase=False,
        bold=False,
    ),
    "mrbeast": CaptionStyle(
        name="mrbeast",
        font="Impact",
        font_size=72,
        primary_rgb=(255, 255, 255),
        highlight_rgb=(255, 80, 80),
        outline_px=8,
        uppercase=True,
    ),
    "tiktok": CaptionStyle(
        name="tiktok",
        font="Montserrat",
        font_size=58,
        primary_rgb=(255, 255, 255),
        highlight_rgb=(0, 220, 255),
        outline_px=4,
        border_style=1,
        uppercase=False,
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
        style: CaptionStyle | str = "bold_outline",
        *,
        video_size: tuple[int, int] = (1080, 1920),
    ) -> None:
        if isinstance(style, str):
            if style not in CAPTION_PRESETS:
                raise ValueError(f"Unknown caption preset: {style}")
            self.style = CAPTION_PRESETS[style]
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
    ) -> CaptionArtifacts:
        """Write caption files and return their paths.

        ``clip_offset`` shifts every timestamp so you can feed a full-length
        transcript and emit captions for just one clip window.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        artifacts = CaptionArtifacts()

        filtered = self._filter_segments(transcript, clip_offset, clip_end)

        if "ass" in formats:
            ass_path = out_dir / f"{base_name}.ass"
            ass_path.write_text(self._build_ass(filtered), encoding="utf-8")
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

    # ---- Filtering ---------------------------------------------------------

    def _filter_segments(
        self,
        transcript: Transcript,
        offset: float,
        end: float | None,
    ) -> list[TranscriptSegment]:
        out: list[TranscriptSegment] = []
        for seg in transcript.segments:
            # Keep segments that overlap the clip window.
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

    def _build_ass(self, segments: list[TranscriptSegment]) -> str:
        style = self.style
        w, h = self.video_size
        primary = _rgb_to_ass_bgr(style.primary_rgb)
        outline = _rgb_to_ass_bgr(style.outline_rgb)
        back = _rgb_to_ass_bgr(style.back_rgb)
        highlight = _rgb_to_ass_bgr(style.highlight_rgb)
        bold = -1 if style.bold else 0
        italic = -1 if style.italic else 0

        header = (
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
            f"2,40,40,{style.bottom_margin_px},1\n"
            "\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

        lines = [header]
        for seg in segments:
            # Group words into rendering lines ~max_words_per_line each.
            line_events = _split_into_lines(
                seg,
                max_chars=style.max_chars_per_line,
                max_words=style.max_words_per_line,
                uppercase=style.uppercase,
                highlight=highlight,
            )
            for start, end, text in line_events:
                lines.append(
                    f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{text}\n"
                )
        return "".join(lines)

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


# ---- Helpers ---------------------------------------------------------------

def _rgb_to_ass_bgr(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"&H00{b:02X}{g:02X}{r:02X}"


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
) -> list[tuple[float, float, str]]:
    """Build one or more ASS events for a single transcript segment.

    If we have word timestamps, emit a karaoke-style event per line where
    the currently-active word is colored with the ``highlight`` color via
    ``{\\r}`` style overrides.
    """
    if not seg.words:
        text = seg.text.upper() if uppercase else seg.text
        return [(seg.start, seg.end, text)]

    # Chunk words into lines.
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
        # Build a text with {\r}...{\r} highlight flips per word so each word
        # flashes highlight for its own duration.
        pieces: list[str] = []
        for w in chunk:
            raw = w.word.strip()
            if uppercase:
                raw = raw.upper()
            dur_cs = max(1, int(round((w.end - w.start) * 100)))
            # \k highlights over duration (centiseconds) using the SecondaryColour,
            # which we've set to `highlight` via the V4+ style.
            pieces.append(f"{{\\k{dur_cs}}}{_ass_escape(raw)} ")
        text = "".join(pieces).rstrip()
        out.append((line_start, line_end, text))
    return out


def _ass_escape(text: str) -> str:
    return text.replace("{", "\\{").replace("}", "\\}").replace("\\N", " ")
