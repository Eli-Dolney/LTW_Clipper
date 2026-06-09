"""Studio tab — review clip plan, transcripts, and reframe previews."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from ..theme import get_font, theme


class StudioTab(ctk.CTkFrame):
    """Review ``plan.json``, transcripts, and per-clip reframe previews."""

    def __init__(
        self,
        parent,
        on_status_change: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_status_change = on_status_change
        self.project_dir: Path | None = None
        self._clips: List[Dict[str, Any]] = []
        self._source_video: Path | None = None
        self._preview_images: list[ctk.CTkLabel] = []
        self._create_widgets()

    def _create_widgets(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=theme.spacing.lg, pady=theme.spacing.lg)

        ctk.CTkLabel(
            scroll, text="🎬  Studio",
            font=get_font("2xl", "bold"), text_color=theme.colors.text_primary,
        ).pack(anchor="w")
        ctk.CTkLabel(
            scroll,
            text="Review clips, transcript, and preview reframed layouts before full render.",
            font=get_font("md"), text_color=theme.colors.text_secondary,
        ).pack(anchor="w", pady=(theme.spacing.xs, theme.spacing.lg))

        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, theme.spacing.md))
        self.path_var = ctk.StringVar(value="")
        ctk.CTkEntry(row, textvariable=self.path_var, font=get_font("sm"), **theme.get_input_style()).pack(
            side="left", fill="x", expand=True, padx=(0, theme.spacing.sm)
        )
        ctk.CTkButton(
            row, text="Browse", width=80, command=self._browse,
            **theme.get_button_style("secondary"),
        ).pack(side="left", padx=(0, theme.spacing.sm))
        ctk.CTkButton(
            row, text="Refresh", width=80, command=self._load_project,
            **theme.get_button_style("primary"),
        ).pack(side="left")

        self.summary_label = ctk.CTkLabel(
            scroll, text="No project loaded.",
            font=get_font("sm"), text_color=theme.colors.text_muted,
        )
        self.summary_label.pack(anchor="w", pady=(0, theme.spacing.md))

        # Preview controls
        preview_card = ctk.CTkFrame(
            scroll, fg_color=theme.colors.bg_secondary, corner_radius=8,
        )
        preview_card.pack(fill="x", pady=(0, theme.spacing.md))
        ctk.CTkLabel(
            preview_card, text="👁  Reframe Preview",
            font=get_font("md", "bold"), text_color=theme.colors.text_primary,
        ).pack(anchor="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm))

        ctrl = ctk.CTkFrame(preview_card, fg_color="transparent")
        ctrl.pack(fill="x", padx=theme.spacing.md, pady=(0, theme.spacing.sm))

        ctk.CTkLabel(ctrl, text="Layout", font=get_font("xs"),
                     text_color=theme.colors.text_secondary).pack(side="left")
        self.preview_layout_var = ctk.StringVar(value="crop")
        ctk.CTkOptionMenu(
            ctrl, values=["crop", "fit", "blur"], variable=self.preview_layout_var,
            width=100, font=get_font("xs"),
            fg_color=theme.colors.bg_tertiary, button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary,
        ).pack(side="left", padx=(theme.spacing.xs, theme.spacing.md))

        ctk.CTkLabel(ctrl, text="Aspect", font=get_font("xs"),
                     text_color=theme.colors.text_secondary).pack(side="left")
        self.preview_aspect_var = ctk.StringVar(value="9:16")
        ctk.CTkOptionMenu(
            ctrl, values=["9:16", "1:1", "4:5", "16:9"], variable=self.preview_aspect_var,
            width=80, font=get_font("xs"),
            fg_color=theme.colors.bg_tertiary, button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary,
        ).pack(side="left", padx=(theme.spacing.xs, theme.spacing.md))

        ctk.CTkLabel(ctrl, text="Zoom", font=get_font("xs"),
                     text_color=theme.colors.text_secondary).pack(side="left")
        self.preview_zoom_slider = ctk.CTkSlider(
            ctrl, from_=0.8, to=1.4, number_of_steps=12, width=120,
            fg_color=theme.colors.bg_tertiary,
            progress_color=theme.colors.accent_primary,
            button_color=theme.colors.accent_primary,
        )
        self.preview_zoom_slider.set(1.0)
        self.preview_zoom_slider.pack(side="left", padx=(theme.spacing.xs, 0))

        self.preview_frame = ctk.CTkFrame(preview_card, fg_color="transparent")
        self.preview_frame.pack(fill="x", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        self.preview_status = ctk.CTkLabel(
            preview_card, text="Select a clip and click Preview Reframe.",
            font=get_font("xs"), text_color=theme.colors.text_muted,
        )
        self.preview_status.pack(anchor="w", padx=theme.spacing.md, pady=(0, theme.spacing.md))

        # Transcript panel
        transcript_card = ctk.CTkFrame(
            scroll, fg_color=theme.colors.bg_secondary, corner_radius=8,
        )
        transcript_card.pack(fill="x", pady=(0, theme.spacing.md))
        ctk.CTkLabel(
            transcript_card, text="📝  Transcript",
            font=get_font("md", "bold"), text_color=theme.colors.text_primary,
        ).pack(anchor="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm))
        self.transcript_box = ctk.CTkTextbox(
            transcript_card, height=140, font=get_font("xs"),
            fg_color=theme.colors.bg_tertiary, text_color=theme.colors.text_secondary,
        )
        self.transcript_box.pack(fill="x", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        self.transcript_box.configure(state="disabled")

        self.grid_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True)

        actions = ctk.CTkFrame(scroll, fg_color="transparent")
        actions.pack(fill="x", pady=theme.spacing.lg)
        ctk.CTkButton(
            actions, text="▶ Run pipeline on source video",
            command=self._run_pipeline,
            **theme.get_button_style("primary"),
        ).pack(fill="x")

    def _browse(self):
        path = filedialog.askdirectory(title="Select LTW project folder")
        if path:
            self.path_var.set(path)
            self._load_project()

    def _load_project(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        for w in self.preview_frame.winfo_children():
            w.destroy()
        self._preview_images.clear()

        raw = self.path_var.get().strip()
        if not raw:
            return
        project = Path(raw)
        plan_path = project / "plan.json"
        if not plan_path.is_file():
            self.summary_label.configure(text="plan.json not found in folder.")
            return

        self.project_dir = project
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        clips = plan.get("clips", [])
        self._clips = clips
        gen = plan.get("generator", "unknown")
        self.summary_label.configure(
            text=f"{len(clips)} clips · generator: {gen} · {project.name}"
        )

        manifest = project / "manifest.json"
        self._source_video = None
        if manifest.is_file():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            src = Path(data.get("source_video", ""))
            if src.is_file():
                self._source_video = src

        self._load_transcript(project)

        for i, clip in enumerate(clips):
            self._add_clip_card(clip, i)

        if self.on_status_change:
            self.on_status_change("Studio loaded", "success")

    def _load_transcript(self, project: Path) -> None:
        self.transcript_box.configure(state="normal")
        self.transcript_box.delete("1.0", "end")
        tpath = project / "transcript.json"
        txt_path = project / "transcript.txt"
        if tpath.is_file():
            data = json.loads(tpath.read_text(encoding="utf-8"))
            lines = []
            for seg in data.get("segments", [])[:80]:
                start = seg.get("start", 0)
                mm, ss = int(start) // 60, int(start) % 60
                lines.append(f"[{mm:02d}:{ss:02d}] {seg.get('text', '').strip()}")
            if len(data.get("segments", [])) > 80:
                lines.append(f"... +{len(data['segments']) - 80} more segments")
            self.transcript_box.insert("1.0", "\n".join(lines))
        elif txt_path.is_file():
            self.transcript_box.insert("1.0", txt_path.read_text(encoding="utf-8")[:8000])
        else:
            self.transcript_box.insert("1.0", "No transcript yet — run the pipeline first.")
        self.transcript_box.configure(state="disabled")

    def _add_clip_card(self, clip: Dict[str, Any], index: int):
        slug = self._slug_from_clip(clip)
        clip_dir = self.project_dir / "clips" / slug if self.project_dir else None
        thumb = clip_dir / "thumbnail.jpg" if clip_dir else None

        card = ctk.CTkFrame(
            self.grid_frame, fg_color=theme.colors.bg_secondary, corner_radius=8,
        )
        card.pack(fill="x", pady=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=theme.spacing.md, pady=theme.spacing.sm)

        if thumb and thumb.is_file():
            try:
                img = ctk.CTkImage(light_image=str(thumb), dark_image=str(thumb), size=(160, 90))
                ctk.CTkLabel(inner, image=img, text="").pack(side="left", padx=(0, theme.spacing.md))
            except Exception:
                ctk.CTkLabel(inner, text="🎞", font=get_font("xl")).pack(side="left", padx=(0, theme.spacing.md))
        else:
            ctk.CTkLabel(inner, text="🎞", font=get_font("xl")).pack(side="left", padx=(0, theme.spacing.md))

        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        title = clip.get("title") or f"Clip {index + 1}"
        score = clip.get("virality_score", 0)
        dur = float(clip.get("end", 0)) - float(clip.get("start", 0))
        ctk.CTkLabel(
            info, text=title, font=get_font("md", "bold"),
            text_color=theme.colors.text_primary, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            info,
            text=f"Score {score:.0%} · {dur:.0f}s · {clip.get('start', 0):.1f}s–{clip.get('end', 0):.1f}s",
            font=get_font("xs"), text_color=theme.colors.text_secondary, anchor="w",
        ).pack(anchor="w")
        hook = (clip.get("hook") or "")[:120]
        if hook:
            ctk.CTkLabel(
                info, text=hook, font=get_font("xs"),
                text_color=theme.colors.text_muted, anchor="w", wraplength=520,
            ).pack(anchor="w")

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=theme.spacing.md, pady=(0, theme.spacing.xs))
        ctk.CTkButton(
            btn_row, text="Preview Reframe", width=120, height=28,
            font=get_font("xs"),
            command=lambda c=clip: self._preview_clip(c),
            **theme.get_button_style("secondary"),
        ).pack(side="right")

        variants = []
        if clip_dir and clip_dir.is_dir():
            variants = [p.name for p in clip_dir.glob("clip_*.mp4")]
        status = "✅ rendered" if thumb and thumb.is_file() else "⏳ planned"
        if variants:
            status += f" · {', '.join(variants[:3])}"
        ctk.CTkLabel(
            btn_row, text=status, font=get_font("xs"),
            text_color=theme.colors.success if "rendered" in status else theme.colors.warning,
        ).pack(side="left")

    def _preview_clip(self, clip: Dict[str, Any]) -> None:
        if not self._source_video or not self._source_video.is_file():
            messagebox.showwarning("Preview", "Source video not found. Load a project with manifest.json.")
            return

        self.preview_status.configure(text="Generating preview…")
        layout = self.preview_layout_var.get()
        aspect_str = self.preview_aspect_var.get()
        aw, ah = (int(x) for x in aspect_str.split(":"))
        zoom = float(self.preview_zoom_slider.get())
        ts = float(clip.get("start", 0)) + 0.5

        def work():
            try:
                from ...core.reframe.renderer import ReframeRenderer, RenderConfig
                from ...core.reframe.tracker import TrackerConfig
                from ...config import get_settings

                settings = get_settings()
                renderer = ReframeRenderer(
                    tracker_config=TrackerConfig(
                        target_aspect=(aw, ah),
                        zoom=zoom,
                        smoothing=settings.reframe.smoothing,
                        headroom=settings.reframe.headroom,
                        max_pan_speed=settings.reframe.max_pan_speed,
                    ),
                    render_config=RenderConfig(layout=layout),  # type: ignore[arg-type]
                )
                out_dir = self.project_dir / "previews" if self.project_dir else Path("/tmp")
                out_dir.mkdir(parents=True, exist_ok=True)
                slug = self._slug_from_clip(clip)
                img_path = out_dir / f"{slug}_{aspect_str.replace(':', 'x')}_{layout}.jpg"
                renderer.preview_overlay(
                    self._source_video,
                    img_path,
                    target_aspect=(aw, ah),
                    layout=layout,  # type: ignore[arg-type]
                    timestamp=ts,
                )
                self.after(0, lambda: self._show_preview_image(img_path, layout, aspect_str))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda e=exc: self.preview_status.configure(text=f"Preview failed: {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _show_preview_image(self, path: Path, layout: str, aspect: str) -> None:
        for w in self.preview_frame.winfo_children():
            w.destroy()
        self._preview_images.clear()
        try:
            h = 240 if aspect == "9:16" else 180
            w = int(h * int(aspect.split(":")[0]) / int(aspect.split(":")[1]))
            img = ctk.CTkImage(light_image=str(path), dark_image=str(path), size=(w, h))
            lbl = ctk.CTkLabel(self.preview_frame, image=img, text="")
            lbl.pack(side="left", padx=4)
            self._preview_images.append(lbl)
            self.preview_status.configure(
                text=f"Preview: {layout} · {aspect} · saved to {path.name}"
            )
        except Exception as exc:
            self.preview_status.configure(text=f"Could not display preview: {exc}")

    @staticmethod
    def _slug_from_clip(clip: Dict[str, Any]) -> str:
        import re
        title = clip.get("title") or f"clip_{int(clip.get('start', 0))}"
        return re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")[:60] or "clip"

    def _run_pipeline(self):
        if not self.project_dir:
            messagebox.showwarning("Studio", "Load a project folder first (or pick a source video).")
            return
        manifest = self.project_dir / "manifest.json"
        source = self._source_video
        if not source or not source.is_file():
            if manifest.is_file():
                data = json.loads(manifest.read_text(encoding="utf-8"))
                source = Path(data.get("source_video", ""))
        if not source or not source.is_file():
            path = filedialog.askopenfilename(
                title="Select source video",
                filetypes=[("Video", "*.mp4 *.mov *.mkv")],
            )
            if not path:
                return
            source = Path(path)

        def work():
            try:
                from ...core.opus_clip_processor import OpusClipProcessor, PipelineOptions
                from ...config import get_settings

                settings = get_settings()
                proc = OpusClipProcessor(PipelineOptions(
                    max_clips=10,
                    whisper_model=settings.whisper.model,
                    use_ollama=settings.ollama.enabled,
                    ollama_host=settings.ollama.host,
                    ollama_model=settings.ollama.model,
                    caption_preset=settings.captions.preset,
                    burn_captions=settings.captions.burn_in,
                    reframe_layout=settings.reframe.layout,
                    reframe_zoom=settings.reframe.zoom,
                    reframe_smoothing=settings.reframe.smoothing,
                    reframe_headroom=settings.reframe.headroom,
                    reframe_max_pan_speed=settings.reframe.max_pan_speed,
                    resume=True,
                ))
                proc.run(source, self.project_dir.parent, project_name=self.project_dir.name)
                self.after(0, self._load_project)
                self.after(0, lambda: messagebox.showinfo("Studio", "Pipeline finished."))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda e=exc: messagebox.showerror("Pipeline error", str(e)))

        threading.Thread(target=work, daemon=True).start()

    def load_project_path(self, path: Path) -> None:
        self.path_var.set(str(path))
        self._load_project()
