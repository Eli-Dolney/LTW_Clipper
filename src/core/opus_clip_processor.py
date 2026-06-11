"""End-to-end local Opus-style pipeline.

Stages:

1. Probe the source video (ffprobe).
2. Transcribe locally with faster-whisper -> :class:`Transcript`.
3. Heuristic scoring + optional Ollama re-ranking -> :class:`ClipPlan`.
4. For each selected clip:
   - Extract a horizontal (original aspect) clip.
   - Extract / render a smart 9:16 portrait clip with face tracking.
   - Generate captions (ASS + SRT + VTT) scoped to the clip window.
   - Optionally burn the ASS into the portrait clip.
   - Generate a thumbnail from the mid-point of the clip.
   - Build publish-ready metadata (YouTube title/description/tags,
     Shorts caption/hashtags, chapters).
5. Write per-clip bundle + a top-level ``plan.json`` manifest.

Everything runs locally. No API keys, no network I/O beyond the optional
Ollama localhost call for title/description polish.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .ai.heuristic_scorer import ScoringWeights
from .ai.highlight_engine import EngineConfig, HighlightEngine
from .ai.metadata_writer import MetadataConfig, MetadataWriter
from .ai.ollama_client import OllamaConfig
from .ai.transcriber import LocalTranscriber, TranscriberConfig
from .captions.burner import CaptionBurner
from .captions.models import CaptionStyleModel, TextOverlayModel
from .captions.styler import CaptionStyler
from .captions.style_manager import StyleManager
from .models import (
    ClipMetadata,
    ClipPlan,
    ClipSuggestion,
    JobContext,
    Transcript,
)
from .reframe.platform_specs import ReframeTarget, default_targets, platforms_to_targets
from .reframe.renderer import LayoutMode, ReframeRenderer, RenderConfig
from .reframe.tracker import TrackerConfig
from .ai.rough_draft_writer import write_rough_draft
from .render.ffmpeg import FFmpegRunner, detect_hwaccel, ffmpeg_available, probe_media
from .render.manifest import ClipManifestEntry, RunManifest, load_manifest, save_manifest

log = logging.getLogger(__name__)


# ---- Pipeline options ------------------------------------------------------

@dataclass
class PipelineOptions:
    max_clips: int = 10
    target_duration: float = 30.0
    min_duration: float = 8.0
    max_duration: float = 60.0
    whisper_model: str = "small"
    whisper_device: str = "auto"
    use_ollama: bool = True
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    caption_preset: str = "bold_outline"
    caption_style: CaptionStyleModel | None = None
    overlays: list[TextOverlayModel] | None = None
    burn_captions: bool = True
    emit_horizontal: bool = True
    emit_portrait: bool = True
    platforms: list[str] | None = None
    reframe_layout: LayoutMode = "crop"
    reframe_zoom: float = 1.0
    reframe_smoothing: float = 0.35
    reframe_headroom: float = 0.08
    reframe_max_pan_speed: float = 0.18
    render_crf: int = 20
    render_preset: str = "medium"
    force_encoder: str | None = None  # "auto" | "videotoolbox" | ... | "cpu"
    render_concurrency: int = 0
    resume: bool = True

    # ---- Channel-template tuning (all optional) ----------------------------
    template_name: str = ""
    hook_phrases: list[str] | None = None
    hook_words: list[str] | None = None
    scoring_weights: dict[str, float] | None = None
    voice_block: str = ""
    extra_hashtags: list[str] | None = None
    extra_tags: list[str] | None = None

    @classmethod
    def from_template(cls, template, **overrides) -> "PipelineOptions":
        """Build options from a :class:`ChannelTemplate`.

        Any keyword in ``overrides`` (e.g. whisper_model, use_ollama) wins over
        the template, so runtime/system settings stay separate from niche tuning.
        """
        opts = cls(
            max_clips=template.max_clips,
            target_duration=template.clip_duration,
            min_duration=template.min_duration,
            max_duration=template.max_duration,
            caption_preset=template.look.caption_preset,
            caption_style=template.look.caption_style,
            overlays=list(template.look.overlays) or None,
            burn_captions=template.add_captions,
            platforms=list(template.platforms),
            template_name=template.name,
            hook_phrases=list(template.hook_phrases) or None,
            hook_words=list(template.hook_words) or None,
            scoring_weights=template.scoring_weights.as_dict(),
            voice_block=template.voice.prompt_block(),
            extra_hashtags=list(template.voice.hashtag_sets) or None,
            extra_tags=list(template.voice.keyword_tags) or None,
        )
        for key, value in overrides.items():
            if hasattr(opts, key):
                setattr(opts, key, value)
        return opts


# ---- Progress reporting ----------------------------------------------------

Stage = str  # "probe" | "transcribe" | "plan" | "render" | "captions" | "metadata" | "package"
ProgressCallback = Callable[[Stage, float, str], None]


def _noop_progress(stage: str, progress: float, message: str) -> None:
    log.debug("[%s] %3.0f%% - %s", stage, progress * 100, message)


# ---- Pipeline --------------------------------------------------------------

class OpusClipProcessor:
    """Run the full local clip-generation pipeline on a single video."""

    def __init__(self, options: PipelineOptions | None = None) -> None:
        self.options = options or PipelineOptions()
        self._cancelled = False

    # ---- Public API --------------------------------------------------------

    def cancel(self) -> None:
        """Signal the pipeline to stop after the current stage."""
        self._cancelled = True

    def run(
        self,
        source: Path,
        output_root: Path,
        *,
        project_name: str | None = None,
        progress: ProgressCallback | None = None,
    ) -> JobContext:
        """Execute the full pipeline for ``source``."""
        self._cancelled = False
        cb = progress or _noop_progress

        if not ffmpeg_available():
            raise RuntimeError("ffmpeg is required but not found on PATH.")

        ctx = JobContext(
            source_video=source,
            output_root=output_root,
            project_name=project_name or source.stem,
        )
        ctx.ensure_dirs()
        manifest_path = ctx.project_dir / "manifest.json"
        run_manifest: RunManifest | None = None
        if self.options.resume:
            run_manifest = load_manifest(manifest_path)

        # -- Probe -----------------------------------------------------------
        cb("probe", 0.02, f"Probing {source.name}")
        probe = probe_media(source)
        log.info("Probed %s: %.2fs @ %.2f fps, %dx%d",
                 source.name, probe.duration, probe.fps, probe.width, probe.height)
        self._checkpoint()

        # -- Transcribe (skip if resuming with cached transcript) ------------
        if (
            run_manifest
            and run_manifest.stage in ("plan", "render", "package", "done")
            and ctx.transcript_path.is_file()
        ):
            cb("transcribe", 0.35, "Using cached transcript")
            ctx.transcript = Transcript.model_validate_json(
                ctx.transcript_path.read_text(encoding="utf-8")
            )
            transcript = ctx.transcript
        else:
            cb("transcribe", 0.05, "Transcribing (local Whisper)")
            transcript = self._transcribe(source)
            ctx.transcript = transcript
            ctx.transcript_path.write_text(transcript.model_dump_json(indent=2), encoding="utf-8")
            cb("transcribe", 0.35, f"{len(transcript.segments)} segments")
            if run_manifest:
                run_manifest.stage = "transcribe"
                save_manifest(manifest_path, run_manifest)
        self._checkpoint()

        # -- Plan (skip if resuming with cached plan) ------------------------
        if (
            run_manifest
            and run_manifest.stage in ("render", "package", "done")
            and ctx.plan_path.is_file()
        ):
            cb("plan", 0.45, "Using cached clip plan")
            plan = ClipPlan.model_validate_json(ctx.plan_path.read_text(encoding="utf-8"))
            ctx.plan = plan
        else:
            cb("plan", 0.38, "Scoring highlights")
            plan = self._plan(source, transcript)
            ctx.plan = plan
            ctx.plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
            cb("plan", 0.45, f"{len(plan.clips)} clips proposed ({plan.generator})")

        run_manifest = RunManifest(
            source_video=str(source),
            project_name=ctx.project_name,
            run_id=ctx.run_id,
            generator=plan.generator,
            stage="render",
            clips=[
                ClipManifestEntry(
                    slug=self._slug_for_clip(c, transcript, source),
                    start=c.start,
                    end=c.end,
                )
                for c in plan.clips
            ],
            completed_slugs=list(run_manifest.completed_slugs) if run_manifest else [],
        )
        save_manifest(manifest_path, run_manifest)

        if not plan.clips:
            cb("package", 1.0, "No clips produced - try lowering min_duration.")
            return ctx
        self._checkpoint()

        # -- Per-clip work ---------------------------------------------------
        enc = self.options.force_encoder or "auto"
        runner = FFmpegRunner(video_encoder=self._resolve_encoder(enc))
        reframe_targets = self._reframe_targets()
        tracker_cfg = TrackerConfig(
            target_aspect=reframe_targets[0].aspect if reframe_targets else (9, 16),
            smoothing=self.options.reframe_smoothing,
            headroom=self.options.reframe_headroom,
            max_pan_speed=self.options.reframe_max_pan_speed,
            zoom=self.options.reframe_zoom,
        )
        reframer = ReframeRenderer(
            tracker_config=tracker_cfg,
            render_config=RenderConfig(layout=self.options.reframe_layout),
        )
        burner = CaptionBurner()
        metadata_writer = MetadataWriter(
            MetadataConfig(
                use_ollama=self.options.use_ollama,
                ollama=OllamaConfig(host=self.options.ollama_host, model=self.options.ollama_model),
                voice_block=self.options.voice_block,
                extra_hashtags=self.options.extra_hashtags,
                extra_tags=self.options.extra_tags,
            ),
        )

        completed = set(run_manifest.completed_slugs)
        clips_to_render = [
            c for c in plan.clips
            if self._slug_for_clip(c, transcript, source) not in completed
        ]
        total = max(1, len(clips_to_render))
        for idx, clip in enumerate(clips_to_render, start=1):
            if self._cancelled:
                cb("render", idx / total, "Cancelled")
                break
            slug = self._slug_for_clip(clip, transcript, source)
            frac = 0.45 + (idx / total) * 0.50
            cb("render", frac, f"Clip {idx}/{total}: {clip.title or slug}")
            try:
                clip_dir = self._render_clip(
                ctx=ctx,
                clip=clip,
                source=source,
                runner=runner,
                reframer=reframer,
                reframe_targets=reframe_targets,
                burner=burner,
                metadata_writer=metadata_writer,
                transcript=transcript,
                probe_duration=probe.duration,
                )
                ctx.rendered_clip_dirs.append(clip_dir)
                run_manifest.completed_slugs.append(slug)
                for entry in run_manifest.clips:
                    if entry.slug == slug:
                        entry.status = "done"
                        entry.clip_dir = str(clip_dir)
                save_manifest(manifest_path, run_manifest)
            except Exception as exc:
                log.exception("Clip render failed: %s", slug)
                for entry in run_manifest.clips:
                    if entry.slug == slug:
                        entry.status = "failed"
                        entry.error = str(exc)
                save_manifest(manifest_path, run_manifest)
                raise

        # -- Package ---------------------------------------------------------
        cb("package", 0.98, "Writing manifest & rough draft")
        try:
            write_rough_draft(
                ctx.project_dir,
                transcript=transcript,
                plan=plan,
                source_title=source.stem,
            )
        except Exception as exc:
            log.warning("Rough draft export failed: %s", exc)
        run_manifest.stage = "done"
        save_manifest(manifest_path, run_manifest)
        self._write_manifest(ctx)
        cb("package", 1.0, f"Done. {len(ctx.rendered_clip_dirs)} clips in {ctx.project_dir}")
        return ctx

    # ---- Stage implementations ---------------------------------------------

    def _transcribe(self, source: Path) -> Transcript:
        transcriber = LocalTranscriber(
            TranscriberConfig(
                model=self.options.whisper_model,
                device=self.options.whisper_device,
            )
        )
        t0 = time.time()
        transcript = transcriber.transcribe(source)
        log.info("Transcribed in %.1fs (%s segments)", time.time() - t0, len(transcript.segments))
        return transcript

    def _plan(self, source: Path, transcript: Transcript) -> ClipPlan:
        weights = None
        if self.options.scoring_weights:
            weights = ScoringWeights(**self.options.scoring_weights)
        engine = HighlightEngine(
            EngineConfig(
                max_clips=self.options.max_clips,
                target_duration=self.options.target_duration,
                min_duration=self.options.min_duration,
                max_duration=self.options.max_duration,
                use_ollama=self.options.use_ollama,
                ollama=OllamaConfig(
                    host=self.options.ollama_host,
                    model=self.options.ollama_model,
                ),
                hook_phrases=tuple(self.options.hook_phrases) if self.options.hook_phrases else None,
                hook_words=tuple(self.options.hook_words) if self.options.hook_words else None,
                weights=weights,
                voice_block=self.options.voice_block,
            )
        )
        return engine.plan_clips(source, transcript)

    def _render_clip(
        self,
        *,
        ctx: JobContext,
        clip: ClipSuggestion,
        source: Path,
        runner: FFmpegRunner,
        reframer: ReframeRenderer,
        reframe_targets: list[ReframeTarget],
        burner: CaptionBurner,
        metadata_writer: MetadataWriter,
        transcript: Transcript,
        probe_duration: float,
    ) -> Path:
        safe_start = max(0.0, float(clip.start))
        safe_end = min(probe_duration or clip.end, float(clip.end))
        if safe_end - safe_start < 0.5:
            raise ValueError(f"Clip {clip.title!r} too short after clamping: {safe_end - safe_start:.2f}s")

        meta = metadata_writer.build(clip, transcript, source_title=source.stem)
        slug = meta.slug
        clip_dir = ctx.clips_dir / slug
        clip_dir.mkdir(parents=True, exist_ok=True)

        horizontal_path = clip_dir / "clip.mp4"
        thumb_path = clip_dir / "thumbnail.jpg"

        # 1. Horizontal extract.
        if self.options.emit_horizontal:
            runner.extract_clip(
                source, horizontal_path,
                start=safe_start, end=safe_end,
                crf=self.options.render_crf, preset=self.options.render_preset,
            )

        # 2. Portrait / platform variants via smart reframe.
        portrait_paths: dict[str, Path] = {}
        if self.options.emit_portrait and reframe_targets:
            tmp_cut = clip_dir / "_cut.mp4"
            runner.extract_clip(
                source, tmp_cut,
                start=safe_start, end=safe_end,
                crf=self.options.render_crf, preset=self.options.render_preset,
            )
            tracked = None
            try:
                tracked = reframer.track(tmp_cut)
                for target in reframe_targets:
                    out_path = clip_dir / f"clip_{target.label}.mp4"
                    try:
                        reframer.render(
                            tmp_cut,
                            out_path,
                            reframe=tracked,
                            target_aspect=target.aspect,
                            layout=self.options.reframe_layout,
                            output_resolution=target.resolution,
                            crf=self.options.render_crf,
                            preset=self.options.render_preset,
                        )
                        portrait_paths[target.label] = out_path
                    except Exception as exc:
                        log.warning(
                            "Smart reframe failed for %s (%s); center crop fallback.",
                            target.label, exc,
                        )
                        reframer.render_center(
                            tmp_cut, out_path,
                            target_aspect=target.aspect,
                            output_resolution=target.resolution,
                            crf=self.options.render_crf,
                            preset=self.options.render_preset,
                        )
                        portrait_paths[target.label] = out_path
            except Exception as exc:
                log.warning("Tracking failed (%s); center crop for all aspects.", exc)
                for target in reframe_targets:
                    out_path = clip_dir / f"clip_{target.label}.mp4"
                    reframer.render_center(
                        tmp_cut, out_path,
                        target_aspect=target.aspect,
                        output_resolution=target.resolution,
                        crf=self.options.render_crf,
                        preset=self.options.render_preset,
                    )
                    portrait_paths[target.label] = out_path
            finally:
                try:
                    tmp_cut.unlink(missing_ok=True)
                except OSError:
                    pass

            # Legacy alias: clip_portrait.mp4 -> primary 9:16 (or first target)
            primary = portrait_paths.get("9x16") or next(iter(portrait_paths.values()), None)
            if primary and primary.is_file():
                legacy = clip_dir / "clip_portrait.mp4"
                if legacy != primary:
                    shutil.copy2(primary, legacy)

        # 3. Captions (scoped to the clip window).
        style_mgr = StyleManager()
        resolved_style = style_mgr.resolve(
            self.options.caption_preset,
            self.options.caption_style,
        )
        styler = CaptionStyler(resolved_style)
        clip_duration = safe_end - safe_start
        overlay_metadata = {
            "title": meta.youtube.title,
            "channel": self.options.template_name or "LTW",
            "cta": meta.shorts.caption,
        }
        caption_artifacts = styler.write(
            transcript, clip_dir,
            base_name="captions",
            clip_offset=safe_start,
            clip_end=safe_end,
            overlays=self.options.overlays or [],
            overlay_metadata=overlay_metadata,
            clip_duration=clip_duration,
        )

        # 4. Optionally burn captions into portrait variants.
        if self.options.burn_captions and caption_artifacts.ass:
            for label, path in portrait_paths.items():
                if not path.is_file():
                    continue
                try:
                    burned = clip_dir / f"clip_{label}_captioned.mp4"
                    burner.burn(
                        path, caption_artifacts.ass, burned,
                        crf=self.options.render_crf, preset=self.options.render_preset,
                    )
                    path.unlink(missing_ok=True)
                    burned.rename(path)
                except Exception as exc:
                    log.warning("Caption burn failed for %s/%s: %s", slug, label, exc)
            legacy = clip_dir / "clip_portrait.mp4"
            primary = portrait_paths.get("9x16") or next(iter(portrait_paths.values()), None)
            if primary and legacy != primary and primary.is_file():
                shutil.copy2(primary, legacy)

        # 5. Thumbnail at 20% into the clip.
        try:
            thumb_ts = safe_start + (safe_end - safe_start) * 0.2
            runner.thumbnail(source, thumb_path, timestamp=thumb_ts, width=1280)
        except Exception as exc:
            log.warning("Thumbnail failed for %s: %s", slug, exc)

        # 6. Write metadata + publish-ready text bundles.
        self._write_metadata_bundle(clip_dir, meta)
        return clip_dir

    # ---- Metadata files ----------------------------------------------------

    @staticmethod
    def _write_metadata_bundle(clip_dir: Path, meta: ClipMetadata) -> None:
        (clip_dir / "metadata.json").write_text(
            meta.model_dump_json(indent=2), encoding="utf-8"
        )

        # youtube.txt: copy-paste ready
        lines = [meta.youtube.title, "", meta.youtube.description]
        if meta.youtube.chapters:
            lines.append("")
            lines.append("Chapters:")
            for offset, title in meta.youtube.chapters:
                mm = int(offset) // 60
                ss = int(offset) % 60
                lines.append(f"{mm:02d}:{ss:02d} {title}")
        if meta.youtube.tags:
            lines.append("")
            lines.append("Tags: " + ", ".join(meta.youtube.tags))
        (clip_dir / "youtube.txt").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

        # tiktok.txt
        tk_lines = [meta.shorts.caption]
        if meta.shorts.hashtags:
            tk_lines.append("")
            tk_lines.append(" ".join(meta.shorts.hashtags))
        (clip_dir / "tiktok.txt").write_text("\n".join(tk_lines).strip() + "\n", encoding="utf-8")

    # ---- Manifest ----------------------------------------------------------

    def _write_manifest(self, ctx: JobContext) -> None:
        manifest = {
            "source_video": str(ctx.source_video),
            "project_name": ctx.project_name,
            "run_id": ctx.run_id,
            "generator": ctx.plan.generator if ctx.plan else "",
            "clip_dirs": [str(p) for p in ctx.rendered_clip_dirs],
        }
        (ctx.project_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

    # ---- Helpers -----------------------------------------------------------

    def _reframe_targets(self) -> list[ReframeTarget]:
        if self.options.platforms:
            targets = platforms_to_targets(self.options.platforms)
            if targets:
                return targets
        return default_targets()

    def _checkpoint(self) -> None:
        if self._cancelled:
            raise RuntimeError("Pipeline cancelled by user")

    @staticmethod
    def _resolve_encoder(force: str) -> str:
        return detect_hwaccel(force)

    @staticmethod
    def _slug_for_clip(clip: ClipSuggestion, transcript: Transcript, source: Path) -> str:
        from .ai.metadata_writer import MetadataWriter

        meta = MetadataWriter(MetadataConfig(use_ollama=False)).build(
            clip, transcript, source_title=source.stem
        )
        return meta.slug
