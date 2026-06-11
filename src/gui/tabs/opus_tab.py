"""Opus Clip AI tab - runs the real local pipeline (no simulation)."""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from ..components.file_picker import FilePicker
from ..components.progress_card import ProgressCard, StageStatus
from ..theme import get_font, theme
from ...core.captions.style_manager import StyleManager


# Map pipeline stage names to indices in the progress card.
STAGE_ORDER = [
    ("probe", "Probing Source"),
    ("transcribe", "Transcribing (local)"),
    ("plan", "Scoring Highlights"),
    ("render", "Rendering Clips"),
    ("package", "Packaging Output"),
]
STAGE_INDEX = {name: i for i, (name, _label) in enumerate(STAGE_ORDER)}


class PlatformCard(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        platform: str,
        icon: str,
        aspect: str,
        selected: bool = False,
        on_toggle: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(
            parent,
            fg_color=theme.colors.bg_tertiary if not selected else theme.colors.accent_primary,
            corner_radius=8,
            cursor="hand2",
            **kwargs,
        )
        self.platform = platform
        self.selected = selected
        self.on_toggle = on_toggle
        self.bind("<Button-1>", self._on_click)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(padx=theme.spacing.md, pady=theme.spacing.sm)
        content.bind("<Button-1>", self._on_click)

        for widget in (
            ctk.CTkLabel(content, text=icon, font=get_font("xl")),
            ctk.CTkLabel(content, text=platform, font=get_font("sm", "bold"),
                         text_color=theme.colors.text_primary),
            ctk.CTkLabel(content, text=aspect, font=get_font("xs"),
                         text_color=theme.colors.text_muted),
        ):
            widget.pack()
            widget.bind("<Button-1>", self._on_click)

    def _on_click(self, event):
        self.selected = not self.selected
        self.configure(fg_color=theme.colors.accent_primary if self.selected else theme.colors.bg_tertiary)
        if self.on_toggle:
            self.on_toggle(self.platform, self.selected)

    def set_selected(self, selected: bool):
        self.selected = selected
        self.configure(fg_color=theme.colors.accent_primary if selected else theme.colors.bg_tertiary)


class OpusTab(ctk.CTkFrame):
    """Opus Clip AI tab - wired to the real pipeline in src.core.opus_clip_processor."""

    def __init__(
        self,
        parent,
        on_status_change: Optional[Callable] = None,
        on_stats_update: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_status_change = on_status_change
        self.on_stats_update = on_stats_update
        self.is_processing = False
        self.selected_files: List[Path] = []
        self.selected_platforms: Dict[str, bool] = {
            "TikTok": True,
            "Instagram Reels": True,
            "YouTube Shorts": True,
            "Twitter": False,
            "LinkedIn": False,
        }
        self._processor = None  # set when a run starts
        self._active_template = None  # ChannelTemplate selected from the Templates tab
        self.style_mgr = StyleManager()
        self._create_widgets()

    # ---- Widgets -----------------------------------------------------------

    def _create_widgets(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True,
                               padx=theme.spacing.lg, pady=theme.spacing.lg)

        # Header
        header = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, theme.spacing.xl))
        ctk.CTkLabel(
            header, text="🤖  Opus Clip AI",
            font=get_font("2xl", "bold"), text_color=theme.colors.text_primary,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Local Whisper + smart reframing. Works offline. Ollama optional for smarter titles.",
            font=get_font("md"), text_color=theme.colors.text_secondary,
        ).pack(anchor="w", pady=(theme.spacing.xs, 0))

        # Active template banner (hidden until a template is applied)
        self.template_banner = ctk.CTkFrame(
            self.scroll_frame, fg_color=theme.colors.bg_tertiary,
            corner_radius=theme.spacing.card_radius,
        )
        self.template_label = ctk.CTkLabel(
            self.template_banner, text="",
            font=get_font("sm", "bold"), text_color=theme.colors.accent_primary,
        )
        self.template_label.pack(side="left", padx=theme.spacing.md, pady=theme.spacing.sm)
        ctk.CTkButton(
            self.template_banner, text="Clear", font=get_font("xs"), width=60, height=26,
            command=self.clear_active_template, **theme.get_button_style("secondary"),
        ).pack(side="right", padx=theme.spacing.md, pady=theme.spacing.sm)

        # File selection
        self._build_file_card()
        self._build_platform_card()
        self._build_ai_settings_card()

        # Progress
        self.progress_card = ProgressCard(
            self.scroll_frame,
            title="Local AI Pipeline",
            stages=[label for _name, label in STAGE_ORDER],
        )
        self.progress_card.pack(fill="x", pady=(0, theme.spacing.lg))

        # Action buttons
        action_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        action_frame.pack(fill="x")
        self.start_btn = ctk.CTkButton(
            action_frame, text="🚀  Start Local Processing",
            font=get_font("md", "bold"), height=48,
            command=self._start_processing,
            **theme.get_button_style("primary"),
        )
        self.start_btn.pack(fill="x", pady=(0, theme.spacing.sm))
        self.stop_btn = ctk.CTkButton(
            action_frame, text="⏹️  Stop",
            font=get_font("sm"), height=36, state="disabled",
            command=self._stop_processing,
            **theme.get_button_style("danger"),
        )
        self.stop_btn.pack(fill="x")

    def _build_file_card(self):
        file_card = ctk.CTkFrame(
            self.scroll_frame, fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius,
        )
        file_card.pack(fill="x", pady=(0, theme.spacing.lg))
        ctk.CTkLabel(
            file_card, text="📁  Source Video",
            font=get_font("md", "bold"), text_color=theme.colors.text_primary,
        ).pack(anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.sm))
        self.file_picker = FilePicker(
            file_card, on_files_changed=self._on_files_changed, multiple=False,
        )
        self.file_picker.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))

    def _build_platform_card(self):
        platform_card = ctk.CTkFrame(
            self.scroll_frame, fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius,
        )
        platform_card.pack(fill="x", pady=(0, theme.spacing.lg))
        ctk.CTkLabel(
            platform_card, text="📱  Target Platforms",
            font=get_font("md", "bold"), text_color=theme.colors.text_primary,
        ).pack(anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.sm))
        ctk.CTkLabel(
            platform_card, text="Select platforms to optimize clips for",
            font=get_font("sm"), text_color=theme.colors.text_secondary,
        ).pack(anchor="w", padx=theme.spacing.lg)

        platform_grid = ctk.CTkFrame(platform_card, fg_color="transparent")
        platform_grid.pack(fill="x", padx=theme.spacing.lg, pady=theme.spacing.lg)
        platforms = [
            ("TikTok", "📱", "9:16"),
            ("Instagram Reels", "📷", "9:16"),
            ("YouTube Shorts", "▶️", "9:16"),
            ("Twitter", "🐦", "1:1"),
            ("LinkedIn", "💼", "16:9"),
        ]
        self.platform_cards: Dict[str, PlatformCard] = {}
        for platform, icon, aspect in platforms:
            card = PlatformCard(
                platform_grid, platform=platform, icon=icon, aspect=aspect,
                selected=self.selected_platforms.get(platform, False),
                on_toggle=self._on_platform_toggle,
            )
            card.pack(side="left", padx=(0, theme.spacing.sm))
            self.platform_cards[platform] = card

    def _build_ai_settings_card(self):
        ai_card = ctk.CTkFrame(
            self.scroll_frame, fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius,
        )
        ai_card.pack(fill="x", pady=(0, theme.spacing.lg))

        ctk.CTkLabel(
            ai_card, text="✨  AI Features (100% local)",
            font=get_font("md", "bold"), text_color=theme.colors.text_primary,
        ).pack(anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.md))

        content = ctk.CTkFrame(ai_card, fg_color="transparent")
        content.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))

        self.ai_highlights_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            content, text="AI Highlight Detection",
            variable=self.ai_highlights_var, font=get_font("sm"),
            fg_color=theme.colors.accent_primary, hover_color=theme.colors.accent_hover,
        ).pack(anchor="w", pady=(0, theme.spacing.sm))
        ctk.CTkLabel(
            content, text="Deterministic scoring + optional local LLM polish.",
            font=get_font("xs"), text_color=theme.colors.text_muted,
        ).pack(anchor="w", padx=(26, 0), pady=(0, theme.spacing.md))

        self.captions_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            content, text="Burn-in Captions",
            variable=self.captions_var, font=get_font("sm"),
            fg_color=theme.colors.accent_primary, hover_color=theme.colors.accent_hover,
        ).pack(anchor="w", pady=(0, theme.spacing.sm))
        ctk.CTkLabel(
            content, text="Word-level captions from local Whisper.",
            font=get_font("xs"), text_color=theme.colors.text_muted,
        ).pack(anchor="w", padx=(26, 0), pady=(0, theme.spacing.md))

        self.use_ollama_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            content, text="Use Ollama for titles/descriptions (if running)",
            variable=self.use_ollama_var, font=get_font("sm"),
            fg_color=theme.colors.accent_primary, hover_color=theme.colors.accent_hover,
        ).pack(anchor="w", pady=(0, theme.spacing.md))

        # Whisper model
        wrow = ctk.CTkFrame(content, fg_color="transparent")
        wrow.pack(fill="x", pady=(0, theme.spacing.md))
        ctk.CTkLabel(
            wrow, text="Whisper Model",
            font=get_font("sm"), text_color=theme.colors.text_secondary,
        ).pack(anchor="w")
        self.whisper_var = ctk.StringVar(value="small")
        ctk.CTkOptionMenu(
            wrow, values=["tiny", "base", "small", "medium", "large-v3"],
            variable=self.whisper_var, font=get_font("sm"),
            fg_color=theme.colors.bg_tertiary, button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary,
        ).pack(anchor="w", pady=(theme.spacing.xs, 0))

        # Caption preset
        crow = ctk.CTkFrame(content, fg_color="transparent")
        crow.pack(fill="x", pady=(0, theme.spacing.md))
        ctk.CTkLabel(
            crow, text="Caption Style",
            font=get_font("sm"), text_color=theme.colors.text_secondary,
        ).pack(anchor="w")
        self.caption_style_var = ctk.StringVar(value="bold_outline")
        self.caption_style_menu = ctk.CTkOptionMenu(
            crow, values=self.style_mgr.names(),
            variable=self.caption_style_var, font=get_font("sm"),
            fg_color=theme.colors.bg_tertiary, button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary,
        )
        self.caption_style_menu.pack(anchor="w", pady=(theme.spacing.xs, 0))

        # Reframe layout
        lrow = ctk.CTkFrame(content, fg_color="transparent")
        lrow.pack(fill="x", pady=(0, theme.spacing.md))
        ctk.CTkLabel(
            lrow, text="Reframe Layout",
            font=get_font("sm"), text_color=theme.colors.text_secondary,
        ).pack(anchor="w")
        self.reframe_layout_var = ctk.StringVar(value="crop")
        ctk.CTkOptionMenu(
            lrow, values=["crop", "fit", "blur"],
            variable=self.reframe_layout_var, font=get_font("sm"),
            fg_color=theme.colors.bg_tertiary, button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary,
        ).pack(anchor="w", pady=(theme.spacing.xs, 0))
        ctk.CTkLabel(
            lrow,
            text="crop = face-tracked fill · fit = letterbox (nothing cut off) · blur = blurred background",
            font=get_font("xs"), text_color=theme.colors.text_muted, wraplength=520,
        ).pack(anchor="w", pady=(2, 0))

        # Max clips slider
        clips_frame = ctk.CTkFrame(content, fg_color="transparent")
        clips_frame.pack(fill="x")
        ctk.CTkLabel(
            clips_frame, text="Maximum Clips to Generate",
            font=get_font("sm"), text_color=theme.colors.text_secondary,
        ).pack(anchor="w")
        clips_control = ctk.CTkFrame(clips_frame, fg_color="transparent")
        clips_control.pack(fill="x", pady=(theme.spacing.xs, 0))
        self.clips_slider = ctk.CTkSlider(
            clips_control, from_=1, to=30, number_of_steps=29,
            fg_color=theme.colors.bg_tertiary,
            progress_color=theme.colors.accent_primary,
            button_color=theme.colors.accent_primary,
            command=self._on_clips_change,
        )
        self.clips_slider.set(10)
        self.clips_slider.pack(side="left", fill="x", expand=True, padx=(0, theme.spacing.md))
        self.clips_value = ctk.CTkLabel(
            clips_control, text="10",
            font=get_font("md", "bold"), text_color=theme.colors.accent_primary, width=40,
        )
        self.clips_value.pack(side="right")

    # ---- Event handlers ----------------------------------------------------

    def _on_files_changed(self, files: List[Path]):
        self.selected_files = files

    def _on_platform_toggle(self, platform: str, selected: bool):
        self.selected_platforms[platform] = selected

    def _on_clips_change(self, value):
        self.clips_value.configure(text=str(int(value)))

    # ---- Channel template --------------------------------------------------

    def set_active_template(self, template) -> None:
        """Apply a :class:`ChannelTemplate` selected from the Templates tab."""
        self._active_template = template
        # Reflect the template's clip/caption settings in the visible controls.
        self.clips_slider.set(template.max_clips)
        self.clips_value.configure(text=str(template.max_clips))
        self.caption_style_var.set(template.look.caption_preset)
        self.captions_var.set(template.add_captions)
        self.template_label.configure(
            text=f"{template.icon}  Template: {template.name}  ({template.niche})"
        )
        self.template_banner.pack(fill="x", pady=(0, theme.spacing.lg),
                                  before=self.file_picker.master)

    def clear_active_template(self) -> None:
        self._active_template = None
        self.template_banner.pack_forget()
        if self.on_status_change:
            self.on_status_change("Template cleared", "info")

    # ---- Processing --------------------------------------------------------

    def _start_processing(self):
        if not self.selected_files:
            messagebox.showwarning("No File", "Please select a video file first")
            return
        if not any(self.selected_platforms.values()):
            messagebox.showwarning("No Platforms", "Please select at least one target platform")
            return

        self.is_processing = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_card.start_processing()
        if self.on_status_change:
            self.on_status_change("Running local pipeline...", "processing")

        thread = threading.Thread(target=self._process_video, daemon=True)
        thread.start()

    def _process_video(self):
        try:
            # Import lazily to keep GUI startup fast.
            from ...core.opus_clip_processor import OpusClipProcessor, PipelineOptions

            source = Path(self.selected_files[0])
            output_root = source.parent / "ltw_output"

            # Runtime/system settings always come from the visible controls; a
            # channel template only contributes niche tuning (hooks/weights/voice).
            overrides = dict(
                max_clips=int(self.clips_slider.get()),
                whisper_model=self.whisper_var.get(),
                use_ollama=self.use_ollama_var.get(),
                caption_preset=self.caption_style_var.get(),
                burn_captions=self.captions_var.get(),
                platforms=[p for p, sel in self.selected_platforms.items() if sel],
                reframe_layout=self.reframe_layout_var.get(),
            )
            if self._active_template is not None:
                options = PipelineOptions.from_template(self._active_template, **overrides)
            else:
                options = PipelineOptions(**overrides)  # type: ignore[arg-type]
            self._processor = OpusClipProcessor(options)

            def on_progress(stage: str, frac: float, message: str):
                self.after(0, lambda: self._update_progress(stage, frac, message))

            ctx = self._processor.run(
                source,
                output_root,
                project_name=source.stem,
                progress=on_progress,
            )
            self.after(0, lambda: self._on_complete(ctx.project_dir))
        except Exception as exc:  # noqa: BLE001
            self.after(0, lambda e=exc: self._on_error(str(e)))

    def _update_progress(self, stage: str, frac: float, message: str):
        self.progress_card.set_progress(frac, message)
        idx = STAGE_INDEX.get(stage)
        if idx is None:
            return
        for i in range(idx):
            self.progress_card.set_stage(i, StageStatus.COMPLETED)
        self.progress_card.set_stage(idx, StageStatus.IN_PROGRESS)

    def _on_complete(self, project_dir: Path):
        self.is_processing = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_card.complete(success=True)
        if self.on_status_change:
            self.on_status_change("Ready", "success")
        messagebox.showinfo(
            "Complete",
            f"Local pipeline complete!\n\nOutput: {project_dir}",
        )

    def _on_error(self, error: str):
        self.is_processing = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_card.complete(success=False)
        if self.on_status_change:
            self.on_status_change("Error", "error")
        from ..utils.diagnostics import collect_diagnostics, copy_diagnostics_to_clipboard

        diag = collect_diagnostics()
        if messagebox.askyesno(
            "Processing failed",
            f"{error}\n\nCopy full diagnostics to clipboard?",
        ):
            copy_diagnostics_to_clipboard(self.winfo_toplevel(), diag)
        else:
            messagebox.showerror("Error", f"Processing failed:\n\n{error}")

    def _stop_processing(self):
        self.is_processing = False
        if self._processor is not None:
            self._processor.cancel()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_card.reset()
        if self.on_status_change:
            self.on_status_change("Stopped", "warning")

    # ---- Settings <-> preset round-trip ------------------------------------

    def get_settings(self) -> Dict[str, Any]:
        return {
            "platforms": [p for p, s in self.selected_platforms.items() if s],
            "ai_highlights": self.ai_highlights_var.get(),
            "add_captions": self.captions_var.get(),
            "use_ollama": self.use_ollama_var.get(),
            "whisper_model": self.whisper_var.get(),
            "caption_preset": self.caption_style_var.get(),
            "max_clips": int(self.clips_slider.get()),
            "reframe_layout": self.reframe_layout_var.get(),
        }

    def apply_settings(self, settings: Dict[str, Any]):
        if "platforms" in settings:
            lowered = [p.lower().replace(" ", "_") for p in settings["platforms"]]
            for platform in self.selected_platforms:
                selected = platform.lower().replace(" ", "_") in lowered
                self.selected_platforms[platform] = selected
                if platform in self.platform_cards:
                    self.platform_cards[platform].set_selected(selected)
        if "ai_highlights" in settings:
            self.ai_highlights_var.set(settings["ai_highlights"])
        if "add_captions" in settings:
            self.captions_var.set(settings["add_captions"])
        if "use_ollama" in settings:
            self.use_ollama_var.set(settings["use_ollama"])
        if "whisper_model" in settings:
            self.whisper_var.set(settings["whisper_model"])
        if "caption_preset" in settings:
            self.caption_style_var.set(settings["caption_preset"])
        if "max_clips" in settings:
            self.clips_slider.set(settings["max_clips"])
            self.clips_value.configure(text=str(settings["max_clips"]))
        if "reframe_layout" in settings:
            self.reframe_layout_var.set(settings["reframe_layout"])
