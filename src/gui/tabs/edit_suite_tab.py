"""Edit Suite — sports/movie edits with beat sync, audio layering, and reference replication."""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Dict, List, Optional

import customtkinter as ctk

from ..theme import get_font, theme
from ...core.assets import AssetPackManager
from ...core.edit_suite.audio_mixer import AudioMixOptions, AudioMixer
from ...core.edit_suite.beats import detect_beats
from ...core.edit_suite.composer import EditComposer, EditComposeOptions
from ...core.edit_suite.models import BeatMap, EditStyleRecipe, ReferenceAnalysis
from ...core.edit_suite.reference_analyzer import ReferenceAnalyzer
from ...core.render.transitions import TRANSITIONS


class EditSuiteTab(ctk.CTkFrame):
    """Sports & movie edit workstation — layer audio, sync to beats, replicate reference edits."""

    def __init__(
        self,
        parent,
        on_status_change: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_status_change = on_status_change
        self.clips: List[Path] = []
        self.beat_map: Optional[BeatMap] = None
        self.recipe: EditStyleRecipe = EditStyleRecipe.sports_default()
        self._music_lookup: Dict[str, Path] = {}
        self._sfx_lookup: Dict[str, Path] = {}
        # Shared controls — created before widgets so _show_recipe is safe anytime.
        self.transition_var = ctk.StringVar(value=self.recipe.transition)
        self.trans_dur_var = ctk.DoubleVar(value=self.recipe.transition_dur)
        self.music_vol_var = ctk.DoubleVar(value=self.recipe.music_volume)
        self.beats_per_clip_var = ctk.IntVar(value=self.recipe.beats_per_clip)
        self._create_widgets()

    def _create_widgets(self) -> None:
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=theme.spacing.lg, pady=theme.spacing.lg)

        ctk.CTkLabel(
            scroll, text="🎞️  Edit Suite",
            font=get_font("2xl", "bold"), text_color=theme.colors.text_primary,
        ).pack(anchor="w")
        ctk.CTkLabel(
            scroll,
            text="Sports & movie edits — layer fighter/dialog + music, sync to beats, replicate a reference edit.",
            font=get_font("md"), text_color=theme.colors.text_secondary, wraplength=700, justify="left",
        ).pack(anchor="w", pady=(theme.spacing.xs, theme.spacing.lg))

        self._build_reference_card(scroll)
        self._build_clips_card(scroll)
        self._build_beats_card(scroll)
        self._build_audio_card(scroll)
        self._build_montage_card(scroll)
        self._build_render_card(scroll)
        self._show_recipe(self.recipe)

    # ---- Cards --------------------------------------------------------------

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=theme.colors.bg_secondary, corner_radius=8)
        card.pack(fill="x", pady=(0, theme.spacing.md))
        ctk.CTkLabel(
            card, text=title, font=get_font("md", "bold"),
            text_color=theme.colors.text_primary,
        ).pack(anchor="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        return inner

    def _build_reference_card(self, parent):
        c = self._card(parent, "🔍  Reference Edit — analyze & replicate style")
        ctk.CTkLabel(
            c,
            text="Drop in a sports hype reel or movie trailer. We'll read cut cadence, "
                 "audio hit density, and pacing — then apply that recipe to your clips.",
            font=get_font("xs"), text_color=theme.colors.text_muted, wraplength=640, justify="left",
        ).pack(anchor="w", pady=(0, theme.spacing.sm))

        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x")
        self.ref_path_var = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.ref_path_var, font=get_font("sm"),
                     **theme.get_input_style()).pack(side="left", fill="x", expand=True, padx=(0, theme.spacing.sm))
        ctk.CTkButton(
            row, text="Browse…", width=90, command=self._browse_reference,
            **theme.get_button_style("secondary"),
        ).pack(side="left", padx=(0, theme.spacing.xs))
        ctk.CTkButton(
            row, text="Analyze", width=90, command=self._analyze_reference,
            **theme.get_button_style("primary"),
        ).pack(side="left")

        self.recipe_box = ctk.CTkTextbox(c, height=100, font=get_font("xs", mono=True),
                                         fg_color=theme.colors.bg_tertiary)
        self.recipe_box.pack(fill="x", pady=(theme.spacing.sm, theme.spacing.sm))

        row2 = ctk.CTkFrame(c, fg_color="transparent")
        row2.pack(fill="x")
        for label, cmd, style in [
            ("Sports preset", lambda: self._apply_preset("sports"), "secondary"),
            ("Cinematic preset", lambda: self._apply_preset("cinematic"), "secondary"),
            ("Save recipe…", self._save_recipe, "secondary"),
            ("Load recipe…", self._load_recipe, "secondary"),
        ]:
            ctk.CTkButton(
                row2, text=label, font=get_font("xs"), height=30, command=cmd,
                **theme.get_button_style(style),
            ).pack(side="left", padx=(0, theme.spacing.xs))

        self.ref_status = ctk.CTkLabel(c, text="", font=get_font("xs"),
                                       text_color=theme.colors.text_muted)
        self.ref_status.pack(anchor="w")

    def _build_clips_card(self, parent):
        c = self._card(parent, "🎬  Your Clips")
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkButton(
            row, text="➕ Add clips…", command=self._add_clips,
            **theme.get_button_style("secondary"),
        ).pack(side="left", padx=(0, theme.spacing.sm))
        ctk.CTkButton(
            row, text="Clear", command=self._clear_clips,
            **theme.get_button_style("danger"),
        ).pack(side="left")
        self.clips_label = ctk.CTkLabel(
            c, text="No clips added yet.", font=get_font("xs"),
            text_color=theme.colors.text_muted,
        )
        self.clips_label.pack(anchor="w", pady=(theme.spacing.sm, 0))

    def _build_beats_card(self, parent):
        c = self._card(parent, "🎵  Beat Sync")
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text="Music track", font=get_font("xs"),
                     text_color=theme.colors.text_secondary).pack(side="left")
        self.music_var = ctk.StringVar(value="None")
        self.music_menu = ctk.CTkOptionMenu(
            row, values=self._music_choices(), variable=self.music_var, width=200,
            font=get_font("xs"),
            fg_color=theme.colors.bg_tertiary, button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary,
        )
        self.music_menu.pack(side="left", padx=(theme.spacing.xs, theme.spacing.sm))
        ctk.CTkButton(
            row, text="Browse…", width=80, height=28, font=get_font("xs"),
            command=self._browse_music, **theme.get_button_style("secondary"),
        ).pack(side="left", padx=(0, theme.spacing.xs))
        ctk.CTkButton(
            row, text="Detect beats", width=100, height=28, font=get_font("xs"),
            command=self._detect_beats, **theme.get_button_style("primary"),
        ).pack(side="left")

        self.beat_status = ctk.CTkLabel(
            c, text="Add a song to sync cuts to the beat grid.",
            font=get_font("xs"), text_color=theme.colors.text_muted,
        )
        self.beat_status.pack(anchor="w", pady=(theme.spacing.sm, 0))

        ctk.CTkLabel(c, text="Beats per clip segment", font=get_font("xs"),
                     text_color=theme.colors.text_secondary).pack(anchor="w", pady=(theme.spacing.sm, 0))
        ctk.CTkSlider(
            c, from_=1, to=8, number_of_steps=7, variable=self.beats_per_clip_var, width=200,
            fg_color=theme.colors.bg_tertiary,
            progress_color=theme.colors.accent_primary,
            button_color=theme.colors.accent_primary,
        ).pack(anchor="w")

    def _build_audio_card(self, parent):
        c = self._card(parent, "🔊  Audio Layers — dialog + music + announcer")
        ctk.CTkLabel(
            c,
            text="Mix clip audio (fighter, crowd, announcer) with a music bed. "
                 "Music ducks under dialog automatically.",
            font=get_font("xs"), text_color=theme.colors.text_muted, wraplength=640, justify="left",
        ).pack(anchor="w", pady=(0, theme.spacing.sm))

        self.dialog_vol_var = ctk.DoubleVar(value=1.0)
        self.duck_var = ctk.BooleanVar(value=True)
        self._slider(c, "Dialog / clip volume", self.dialog_vol_var, 0.0, 1.5)
        self._slider(c, "Music volume", self.music_vol_var, 0.0, 1.0)

        ann_row = ctk.CTkFrame(c, fg_color="transparent")
        ann_row.pack(fill="x", pady=(theme.spacing.sm, 0))
        ctk.CTkLabel(ann_row, text="Announcer / voice-over", font=get_font("xs"),
                     text_color=theme.colors.text_secondary).pack(side="left")
        self.announcer_var = ctk.StringVar(value="")
        ctk.CTkEntry(ann_row, textvariable=self.announcer_var, font=get_font("xs"),
                     placeholder_text="Optional — touchdown call, hype line…",
                     **theme.get_input_style()).pack(side="left", fill="x", expand=True, padx=(theme.spacing.sm, 0))
        ctk.CTkButton(
            ann_row, text="…", width=32, height=28, command=self._browse_announcer,
            **theme.get_button_style("secondary"),
        ).pack(side="left", padx=(theme.spacing.xs, 0))

        ctk.CTkCheckBox(
            c, text="Duck music under dialog (sidechain)",
            variable=self.duck_var, font=get_font("xs"),
            fg_color=theme.colors.accent_primary,
        ).pack(anchor="w", pady=(theme.spacing.sm, 0))

        mix_row = ctk.CTkFrame(c, fg_color="transparent")
        mix_row.pack(fill="x", pady=(theme.spacing.md, 0))
        ctk.CTkButton(
            mix_row, text="Mix audio on single clip…", command=self._mix_single_clip,
            **theme.get_button_style("secondary"),
        ).pack(side="left")

    def _build_montage_card(self, parent):
        c = self._card(parent, "✂️  Montage Settings")
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text="Transition", font=get_font("xs"),
                     text_color=theme.colors.text_secondary).pack(side="left")
        ctk.CTkOptionMenu(
            row, values=list(TRANSITIONS.keys()), variable=self.transition_var, width=130,
            font=get_font("xs"),
            fg_color=theme.colors.bg_tertiary, button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary,
        ).pack(side="left", padx=(theme.spacing.xs, theme.spacing.md))

        ctk.CTkLabel(row, text="Dur", font=get_font("xs"),
                     text_color=theme.colors.text_secondary).pack(side="left")
        ctk.CTkSlider(
            row, from_=0.15, to=1.0, number_of_steps=17, variable=self.trans_dur_var, width=120,
            fg_color=theme.colors.bg_tertiary,
            progress_color=theme.colors.accent_primary,
            button_color=theme.colors.accent_primary,
        ).pack(side="left", padx=(theme.spacing.xs, theme.spacing.md))

        ctk.CTkLabel(row, text="SFX at cuts", font=get_font("xs"),
                     text_color=theme.colors.text_secondary).pack(side="left")
        self.sfx_var = ctk.StringVar(value="None")
        self.sfx_menu = ctk.CTkOptionMenu(
            row, values=self._sfx_choices(), variable=self.sfx_var, width=150,
            font=get_font("xs"),
            fg_color=theme.colors.bg_tertiary, button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary,
        )
        self.sfx_menu.pack(side="left", padx=(theme.spacing.xs, 0))

    def _build_render_card(self, parent):
        c = self._card(parent, "🚀  Render Edit")
        self.output_var = ctk.StringVar(value=str(Path.home() / "Desktop" / "my_edit.mp4"))
        ctk.CTkLabel(c, text="Output file", font=get_font("xs"),
                     text_color=theme.colors.text_secondary).pack(anchor="w")
        out_row = ctk.CTkFrame(c, fg_color="transparent")
        out_row.pack(fill="x", pady=(theme.spacing.xs, theme.spacing.sm))
        ctk.CTkEntry(out_row, textvariable=self.output_var, font=get_font("sm"),
                     **theme.get_input_style()).pack(side="left", fill="x", expand=True, padx=(0, theme.spacing.sm))
        ctk.CTkButton(
            out_row, text="…", width=32, command=self._browse_output,
            **theme.get_button_style("secondary"),
        ).pack(side="left")

        self.render_btn = ctk.CTkButton(
            c, text="🎬  Build Full Edit", height=44, font=get_font("md", "bold"),
            command=self._render_edit, **theme.get_button_style("primary"),
        )
        self.render_btn.pack(fill="x", pady=(theme.spacing.sm, 0))
        self.render_status = ctk.CTkLabel(
            c, text="", font=get_font("xs"), text_color=theme.colors.text_muted,
        )
        self.render_status.pack(anchor="w", pady=(theme.spacing.sm, 0))

    def _slider(self, parent, label: str, var, lo: float, hi: float) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, font=get_font("xs"),
                     text_color=theme.colors.text_secondary, width=140).pack(side="left")
        ctk.CTkSlider(
            row, from_=lo, to=hi, variable=var, width=200,
            fg_color=theme.colors.bg_tertiary,
            progress_color=theme.colors.accent_primary,
            button_color=theme.colors.accent_primary,
        ).pack(side="left", fill="x", expand=True)

    # ---- Asset helpers ------------------------------------------------------

    def _music_choices(self) -> list[str]:
        choices = ["None"]
        self._music_lookup = {}
        for item in AssetPackManager().items("music"):
            choices.append(item.name)
            self._music_lookup[item.name] = item.path
        for item in AssetPackManager().items("sfx"):
            if item.name not in self._music_lookup:
                choices.append(f"{item.name} (sfx)")
                self._music_lookup[f"{item.name} (sfx)"] = item.path
        return choices

    def _sfx_choices(self) -> list[str]:
        choices = ["None"]
        self._sfx_lookup = {}
        for item in AssetPackManager().items("sfx"):
            choices.append(item.name)
            self._sfx_lookup[item.name] = item.path
        return choices

    def _resolve_music(self) -> Path | None:
        name = self.music_var.get()
        if name == "None":
            return None
        return self._music_lookup.get(name)

    def _resolve_sfx(self) -> Path | None:
        name = self.sfx_var.get()
        if name == "None":
            return None
        return self._sfx_lookup.get(name)

    # ---- Recipe display -----------------------------------------------------

    def _show_recipe(self, recipe: EditStyleRecipe) -> None:
        self.recipe = recipe
        lines = [
            f"Style: {recipe.style_tag}",
            f"Cut rate: {recipe.cuts_per_minute}/min · avg shot {recipe.avg_shot_length}s",
            f"Transition: {recipe.transition} ({recipe.transition_dur}s)",
            f"Music vol {recipe.music_volume} · duck {recipe.music_duck_db} dB · beats/clip {recipe.beats_per_clip}",
        ]
        if hasattr(self, "recipe_box"):
            self.recipe_box.configure(state="normal")
            self.recipe_box.delete("1.0", "end")
            self.recipe_box.insert("1.0", "\n".join(lines))
            self.recipe_box.configure(state="disabled")
        self.transition_var.set(recipe.transition)
        self.trans_dur_var.set(recipe.transition_dur)
        self.music_vol_var.set(recipe.music_volume)
        self.beats_per_clip_var.set(recipe.beats_per_clip)

    # ---- Actions ------------------------------------------------------------

    def _browse_reference(self) -> None:
        path = filedialog.askopenfilename(
            title="Reference edit", filetypes=[("Video", "*.mp4 *.mov *.mkv *.webm")],
        )
        if path:
            self.ref_path_var.set(path)

    def _analyze_reference(self) -> None:
        path = self.ref_path_var.get().strip()
        if not path:
            messagebox.showwarning("Reference", "Pick a reference edit video first.")
            return
        self.ref_status.configure(text="Analyzing reference edit…")

        def work() -> None:
            try:
                analyzer = ReferenceAnalyzer()
                analysis = analyzer.analyze(Path(path), beat_map=self.beat_map)
                self.after(0, lambda: self._on_reference_done(analysis))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda e=exc: self.ref_status.configure(text=f"Analysis failed: {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _on_reference_done(self, analysis) -> None:
        self.recipe = analysis.recipe
        self._show_recipe(self.recipe)
        self.ref_status.configure(
            text=f"✓ {analysis.recipe.style_tag} style — {analysis.recipe.cut_count} cuts, "
                 f"{len(analysis.audio_peak_timestamps)} audio hits detected"
        )
        if self.on_status_change:
            self.on_status_change("Reference style analyzed", "success")

    def _apply_preset(self, kind: str) -> None:
        if kind == "cinematic":
            self._show_recipe(EditStyleRecipe.cinematic_default())
        else:
            self._show_recipe(EditStyleRecipe.sports_default())

    def _save_recipe(self) -> None:
        dest = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("Edit recipe", "*.json")],
        )
        if dest:
            ReferenceAnalyzer().save(ReferenceAnalysis(recipe=self.recipe), Path(dest))

    def _load_recipe(self) -> None:
        src = filedialog.askopenfilename(filetypes=[("Edit recipe", "*.json")])
        if src:
            from ...core.edit_suite.reference_analyzer import ReferenceAnalyzer
            analysis = ReferenceAnalyzer().load(Path(src))
            self._show_recipe(analysis.recipe)

    def _add_clips(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Add clips", filetypes=[("Video", "*.mp4 *.mov *.mkv")],
        )
        for p in paths:
            path = Path(p)
            if path not in self.clips:
                self.clips.append(path)
        self._refresh_clips_label()

    def _clear_clips(self) -> None:
        self.clips.clear()
        self._refresh_clips_label()

    def _refresh_clips_label(self) -> None:
        if not self.clips:
            self.clips_label.configure(text="No clips added yet.")
        else:
            names = ", ".join(c.name for c in self.clips[:6])
            extra = f" (+{len(self.clips) - 6} more)" if len(self.clips) > 6 else ""
            self.clips_label.configure(text=f"{len(self.clips)} clips: {names}{extra}")

    def _browse_music(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.m4a *.flac")])
        if path:
            p = Path(path)
            self._music_lookup[p.stem] = p
            choices = self._music_choices()
            if p.stem not in choices:
                choices.append(p.stem)
            self.music_menu.configure(values=choices)
            self.music_var.set(p.stem)

    def _detect_beats(self) -> None:
        music = self._resolve_music()
        if music is None:
            path = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.m4a")])
            if not path:
                return
            music = Path(path)
        self.beat_status.configure(text="Detecting beats…")

        def work() -> None:
            try:
                bm = detect_beats(music)
                self.after(0, lambda: self._on_beats_done(bm))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda e=exc: self.beat_status.configure(text=f"Beat detection failed: {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _on_beats_done(self, bm: BeatMap) -> None:
        self.beat_map = bm
        self.beat_status.configure(
            text=f"✓ {bm.total_beats} beats @ {bm.tempo:.0f} BPM — segment ~{bm.segment_duration(int(self.beats_per_clip_var.get())):.2f}s"
        )

    def _browse_announcer(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.m4a")])
        if path:
            self.announcer_var.set(path)

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if path:
            self.output_var.set(path)

    def _audio_options(self) -> AudioMixOptions:
        return AudioMixOptions(
            dialog_volume=float(self.dialog_vol_var.get()),
            music_volume=float(self.music_vol_var.get()),
            duck_music=bool(self.duck_var.get()),
        )

    def _mix_single_clip(self) -> None:
        if not self.clips:
            messagebox.showwarning("Mix", "Add at least one clip.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".mp4")
        if not out:
            return
        music = self._resolve_music()
        ann = self.announcer_var.get().strip() or None
        self.render_status.configure(text="Mixing audio…")

        def work() -> None:
            try:
                AudioMixer().mix(
                    self.clips[0], Path(out),
                    music=music,
                    announcer=Path(ann) if ann else None,
                    options=self._audio_options(),
                )
                self.after(0, lambda: self.render_status.configure(text=f"✓ Saved: {out}"))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda e=exc: self.render_status.configure(text=f"Mix failed: {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _render_edit(self) -> None:
        if len(self.clips) < 1:
            messagebox.showwarning("Render", "Add at least one clip.")
            return
        output = Path(self.output_var.get().strip())
        if not output:
            messagebox.showwarning("Render", "Set an output path.")
            return

        self.render_btn.configure(state="disabled")
        self.render_status.configure(text="Building edit…")

        recipe = self.recipe.model_copy()
        recipe.transition = self.transition_var.get()
        recipe.transition_dur = float(self.trans_dur_var.get())
        recipe.music_volume = float(self.music_vol_var.get())
        recipe.beats_per_clip = int(self.beats_per_clip_var.get())

        music = self._resolve_music()
        sfx = self._resolve_sfx()
        ann = self.announcer_var.get().strip() or None
        peaks: list[float] | None = None
        if self.ref_path_var.get().strip():
            try:
                analysis = ReferenceAnalyzer().analyze(Path(self.ref_path_var.get()))
                peaks = analysis.audio_peak_timestamps[:20]
            except Exception:
                peaks = None

        def work() -> None:
            try:
                composer = EditComposer()
                opts = EditComposeOptions(
                    transition=recipe.transition,
                    transition_dur=recipe.transition_dur,
                    beats_per_clip=recipe.beats_per_clip,
                    audio=self._audio_options(),
                )
                composer.compose_with_audio(
                    self.clips, output,
                    music=music,
                    announcer=Path(ann) if ann else None,
                    sfx=sfx,
                    recipe=recipe,
                    beat_map=self.beat_map,
                    analysis_peaks=peaks,
                    options=opts,
                    transition_sfx=sfx,
                )
                self.after(0, lambda: self._on_render_done(output))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda e=exc: self._on_render_fail(e))

        threading.Thread(target=work, daemon=True).start()

    def _on_render_done(self, output: Path) -> None:
        self.render_btn.configure(state="normal")
        self.render_status.configure(text=f"✓ Edit saved: {output}")
        if self.on_status_change:
            self.on_status_change(f"Edit saved: {output.name}", "success")

    def _on_render_fail(self, exc: Exception) -> None:
        self.render_btn.configure(state="normal")
        self.render_status.configure(text=f"Render failed: {exc}")
        messagebox.showerror("Render failed", str(exc))
