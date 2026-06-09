"""Export a human-readable rough draft bundle from pipeline artifacts."""

from __future__ import annotations

from pathlib import Path

from ..models import ClipPlan, Transcript


def _fmt_time(seconds: float) -> str:
    mm = int(seconds) // 60
    ss = int(seconds) % 60
    return f"{mm:02d}:{ss:02d}"


def write_rough_draft(
    project_dir: Path,
    *,
    transcript: Transcript,
    plan: ClipPlan | None = None,
    source_title: str = "",
) -> Path:
    """Write ``rough_draft.md`` with transcript, chapters, and clip notes."""
    lines: list[str] = []
    title = source_title or (plan.source_video.stem if plan else project_dir.name)
    lines.append(f"# Rough Draft — {title}")
    lines.append("")
    lines.append(f"Language: {transcript.language or 'auto'} · "
                 f"Duration: {_fmt_time(transcript.duration)} · "
                 f"{len(transcript.segments)} segments")
    lines.append("")

    # Full transcript
    lines.append("## Full Transcript")
    lines.append("")
    for seg in transcript.segments:
        lines.append(f"**[{_fmt_time(seg.start)} – {_fmt_time(seg.end)}]** {seg.text.strip()}")
    lines.append("")

    # Plain text export alongside markdown
    txt_path = project_dir / "transcript.txt"
    txt_lines = [f"[{_fmt_time(s.start)}] {s.text.strip()}" for s in transcript.segments]
    txt_path.write_text("\n".join(txt_lines).strip() + "\n", encoding="utf-8")

    if plan and plan.clips:
        lines.append("## Proposed Clips")
        lines.append("")
        for i, clip in enumerate(plan.clips, start=1):
            dur = clip.end - clip.start
            lines.append(f"### Clip {i}: {clip.title or f'Highlight {i}'}")
            lines.append("")
            lines.append(f"- **Window:** {_fmt_time(clip.start)} – {_fmt_time(clip.end)} ({dur:.0f}s)")
            lines.append(f"- **Score:** {clip.virality_score:.0%}")
            if clip.hook:
                lines.append(f"- **Hook:** {clip.hook}")
            if clip.caption:
                lines.append(f"- **Caption:** {clip.caption}")
            if clip.tags:
                lines.append(f"- **Tags:** {', '.join(clip.tags)}")
            if clip.rationale:
                lines.append(f"- **Why:** {clip.rationale}")
            lines.append("")
            lines.append("**Transcript excerpt:**")
            lines.append("")
            for seg in transcript.segments:
                if seg.end <= clip.start or seg.start >= clip.end:
                    continue
                lines.append(f"> [{_fmt_time(seg.start)}] {seg.text.strip()}")
            lines.append("")

    out = project_dir / "rough_draft.md"
    out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return out
