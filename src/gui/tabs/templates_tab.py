"""Channel Templates tab.

Pick a niche template (Game Dev, Gaming, Geopolitics, AI, ...), inspect/edit its
hook patterns, scoring weights and channel voice, save custom variants, and send
it straight into the Opus Clip AI pipeline.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk

from ..theme import get_font, theme

from ...core.assets import AssetPackManager
from ...core.templates import ChannelTemplate, TemplateManager
from ...core.captions.style_manager import StyleManager
from ...core.templates.models import LookAndSound, ScoringWeightsModel, VoiceProfile
WEIGHT_FIELDS = ["audio", "hook_phrase", "hook_word", "length", "completeness"]


class TemplatesTab(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        on_status_change: Optional[Callable] = None,
        on_apply_template: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_status_change = on_status_change
        self.on_apply_template = on_apply_template
        self.manager = TemplateManager()
        self.style_mgr = StyleManager()
        self.pack_mgr = AssetPackManager()
        self.current: Optional[ChannelTemplate] = None
        self._list_buttons: dict[str, ctk.CTkButton] = {}
        self._create_widgets()
        # Select the first template by default.
        names = self.manager.names()
        if names:
            self._select(names[0])

    # ---- Layout ------------------------------------------------------------

    def _create_widgets(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.sm))
        ctk.CTkLabel(
            header, text="🎛️  Channel Templates",
            font=get_font("2xl", "bold"), text_color=theme.colors.text_primary,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Niche presets that tune highlight detection, captions, and channel voice.",
            font=get_font("md"), text_color=theme.colors.text_secondary,
        ).pack(anchor="w", pady=(theme.spacing.xs, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=theme.spacing.lg, pady=theme.spacing.md)

        # Left: template list
        left = ctk.CTkFrame(body, fg_color=theme.colors.bg_secondary,
                            corner_radius=theme.spacing.card_radius, width=240)
        left.pack(side="left", fill="y", padx=(0, theme.spacing.md))
        left.pack_propagate(False)
        ctk.CTkLabel(
            left, text="TEMPLATES", font=get_font("xs", "bold"),
            text_color=theme.colors.text_muted,
        ).pack(anchor="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm))
        self.list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=theme.spacing.sm)

        import_btn = ctk.CTkButton(
            left, text="📥  Import…", font=get_font("sm"), height=34,
            command=self._import, **theme.get_button_style("secondary"),
        )
        import_btn.pack(fill="x", padx=theme.spacing.md, pady=(theme.spacing.sm, theme.spacing.md))

        # Right: editor
        self.editor = ctk.CTkScrollableFrame(body, fg_color="transparent")
        self.editor.pack(side="right", fill="both", expand=True)

        self._build_editor()
        self._refresh_list()

    def _refresh_list(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._list_buttons.clear()
        for tpl in self.manager.all():
            label = f"{tpl.icon}  {tpl.name}" + ("" if tpl.builtin else "  •")
            btn = ctk.CTkButton(
                self.list_frame, text=label, font=get_font("sm"),
                height=38, anchor="w",
                fg_color="transparent", hover_color=theme.colors.bg_hover,
                command=lambda n=tpl.name: self._select(n),
            )
            btn.pack(fill="x", pady=1)
            self._list_buttons[tpl.name] = btn

    def _build_editor(self):
        e = self.editor

        # Identity
        self.name_var = ctk.StringVar()
        self.niche_var = ctk.StringVar()
        self.desc_var = ctk.StringVar()
        ident = self._card(e, "Identity")
        self._labeled_entry(ident, "Template Name", self.name_var)
        self._labeled_entry(ident, "Niche", self.niche_var)
        self._labeled_entry(ident, "Description", self.desc_var)

        # Pacing
        pace = self._card(e, "Pacing")
        self.clip_dur_var = ctk.StringVar()
        self.min_dur_var = ctk.StringVar()
        self.max_dur_var = ctk.StringVar()
        self.max_clips_var = ctk.StringVar()
        row = ctk.CTkFrame(pace, fg_color="transparent")
        row.pack(fill="x")
        self._mini_entry(row, "Target (s)", self.clip_dur_var)
        self._mini_entry(row, "Min (s)", self.min_dur_var)
        self._mini_entry(row, "Max (s)", self.max_dur_var)
        self._mini_entry(row, "Max clips", self.max_clips_var)

        # Patterns
        patt = self._card(e, "Patterns — what counts as a highlight")
        ctk.CTkLabel(patt, text="Hook phrases (one per line)", font=get_font("sm"),
                     text_color=theme.colors.text_secondary).pack(anchor="w")
        self.hook_phrases_box = ctk.CTkTextbox(patt, height=110, font=get_font("sm", mono=True))
        self.hook_phrases_box.pack(fill="x", pady=(theme.spacing.xs, theme.spacing.md))
        ctk.CTkLabel(patt, text="Hook words (one per line)", font=get_font("sm"),
                     text_color=theme.colors.text_secondary).pack(anchor="w")
        self.hook_words_box = ctk.CTkTextbox(patt, height=90, font=get_font("sm", mono=True))
        self.hook_words_box.pack(fill="x", pady=(theme.spacing.xs, theme.spacing.md))

        ctk.CTkLabel(patt, text="Scoring weights", font=get_font("sm"),
                     text_color=theme.colors.text_secondary).pack(anchor="w")
        wrow = ctk.CTkFrame(patt, fg_color="transparent")
        wrow.pack(fill="x", pady=(theme.spacing.xs, 0))
        self.weight_vars: dict[str, ctk.StringVar] = {}
        for field in WEIGHT_FIELDS:
            var = ctk.StringVar()
            self.weight_vars[field] = var
            self._mini_entry(wrow, field, var)

        # Voice
        voice = self._card(e, "Channel Voice — feeds titles/descriptions")
        self.persona_var = ctk.StringVar()
        self.tone_var = ctk.StringVar()
        self.title_style_var = ctk.StringVar()
        self.cta_var = ctk.StringVar()
        self._labeled_entry(voice, "Persona", self.persona_var)
        self._labeled_entry(voice, "Tone", self.tone_var)
        self._labeled_entry(voice, "Title style", self.title_style_var)
        self._labeled_entry(voice, "Call to action", self.cta_var)
        ctk.CTkLabel(voice, text="Default hashtags (space or newline separated)",
                     font=get_font("sm"), text_color=theme.colors.text_secondary).pack(anchor="w")
        self.hashtags_box = ctk.CTkTextbox(voice, height=60, font=get_font("sm", mono=True))
        self.hashtags_box.pack(fill="x", pady=(theme.spacing.xs, theme.spacing.md))
        ctk.CTkLabel(voice, text="Keyword tags (comma or newline separated)",
                     font=get_font("sm"), text_color=theme.colors.text_secondary).pack(anchor="w")
        self.keyword_tags_box = ctk.CTkTextbox(voice, height=60, font=get_font("sm", mono=True))
        self.keyword_tags_box.pack(fill="x", pady=(theme.spacing.xs, 0))

        # Look & sound
        look = self._card(e, "Look & Sound")
        crow = ctk.CTkFrame(look, fg_color="transparent")
        crow.pack(fill="x")
        ctk.CTkLabel(crow, text="Caption preset", font=get_font("sm"),
                     text_color=theme.colors.text_secondary).pack(anchor="w")
        self.caption_var = ctk.StringVar(value="bold_outline")
        self.caption_menu = ctk.CTkOptionMenu(
            crow, values=self._caption_style_names(), variable=self.caption_var, font=get_font("sm"),
            fg_color=theme.colors.bg_tertiary, button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary,
        )
        self.caption_menu.pack(anchor="w", pady=(theme.spacing.xs, theme.spacing.md))
        ctk.CTkButton(
            look, text="✏️  Open Text Studio to edit styles",
            font=get_font("xs"), height=28, command=self._open_text_studio_hint,
            **theme.get_button_style("secondary"),
        ).pack(anchor="w", pady=(0, theme.spacing.sm))
        self.lut_var = ctk.StringVar()
        self.transition_pack_var = ctk.StringVar()
        self.sfx_pack_var = ctk.StringVar()
        self._labeled_entry(look, "LUT name (optional)", self.lut_var)
        self.transition_combo = self._labeled_combo(
            look, "Transition pack (optional)", self.transition_pack_var,
            self._pack_choices("transition"))
        self.sfx_combo = self._labeled_combo(
            look, "SFX pack (optional)", self.sfx_pack_var,
            self._pack_choices("sfx"))
        self.auto_trans_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            look, text="Auto-apply transitions + SFX in clip render",
            variable=self.auto_trans_var, font=get_font("sm"),
            fg_color=theme.colors.accent_primary, hover_color=theme.colors.accent_hover,
        ).pack(anchor="w", pady=(theme.spacing.sm, 0))

        # Asset packs (click to add folder)
        self._build_asset_packs_card(e)

        # Actions
        actions = ctk.CTkFrame(e, fg_color="transparent")
        actions.pack(fill="x", pady=theme.spacing.lg)
        self.apply_btn = ctk.CTkButton(
            actions, text="🚀  Use in Opus Clip AI", font=get_font("md", "bold"),
            height=44, command=self._apply, **theme.get_button_style("primary"),
        )
        self.apply_btn.pack(fill="x", pady=(0, theme.spacing.sm))
        row2 = ctk.CTkFrame(actions, fg_color="transparent")
        row2.pack(fill="x")
        ctk.CTkButton(
            row2, text="💾  Save as Custom", font=get_font("sm"), height=36,
            command=self._save, **theme.get_button_style("secondary"),
        ).pack(side="left", fill="x", expand=True, padx=(0, theme.spacing.xs))
        ctk.CTkButton(
            row2, text="📤  Export", font=get_font("sm"), height=36,
            command=self._export, **theme.get_button_style("secondary"),
        ).pack(side="left", fill="x", expand=True, padx=theme.spacing.xs)
        self.delete_btn = ctk.CTkButton(
            row2, text="🗑️  Delete", font=get_font("sm"), height=36,
            command=self._delete, **theme.get_button_style("danger"),
        )
        self.delete_btn.pack(side="left", fill="x", expand=True, padx=(theme.spacing.xs, 0))

    # ---- Small widget helpers ----------------------------------------------

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=theme.colors.bg_secondary,
                            corner_radius=theme.spacing.card_radius)
        card.pack(fill="x", pady=(0, theme.spacing.md))
        ctk.CTkLabel(card, text=title, font=get_font("md", "bold"),
                     text_color=theme.colors.text_primary).pack(
            anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.md, theme.spacing.sm))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.md))
        return inner

    def _labeled_entry(self, parent, label: str, var: ctk.StringVar):
        ctk.CTkLabel(parent, text=label, font=get_font("sm"),
                     text_color=theme.colors.text_secondary).pack(anchor="w")
        ctk.CTkEntry(parent, textvariable=var, font=get_font("sm"),
                     **theme.get_input_style()).pack(
            fill="x", pady=(theme.spacing.xs, theme.spacing.md))

    def _labeled_combo(self, parent, label: str, var: ctk.StringVar, values: list[str]):
        ctk.CTkLabel(parent, text=label, font=get_font("sm"),
                     text_color=theme.colors.text_secondary).pack(anchor="w")
        combo = ctk.CTkComboBox(
            parent, variable=var, values=values, font=get_font("sm"),
            fg_color=theme.colors.bg_tertiary, button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary,
        )
        combo.pack(fill="x", pady=(theme.spacing.xs, theme.spacing.md))
        return combo

    def _mini_entry(self, parent, label: str, var: ctk.StringVar):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="left", fill="x", expand=True, padx=(0, theme.spacing.sm))
        ctk.CTkLabel(frame, text=label, font=get_font("xs"),
                     text_color=theme.colors.text_muted).pack(anchor="w")
        ctk.CTkEntry(frame, textvariable=var, font=get_font("sm"),
                     **theme.get_input_style()).pack(fill="x", pady=(2, 0))

    # ---- Asset packs -------------------------------------------------------

    def _caption_style_names(self) -> list[str]:
        return self.style_mgr.names()

    def _open_text_studio_hint(self) -> None:
        if self.on_status_change:
            self.on_status_change("Open the Text Studio tab to design caption styles", "info")

    def _pack_choices(self, kind: str) -> list[str]:
        return [""] + self.pack_mgr.pack_names(kind)

    def _build_asset_packs_card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=theme.colors.bg_secondary,
                            corner_radius=theme.spacing.card_radius)
        card.pack(fill="x", pady=(0, theme.spacing.md))
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=theme.spacing.lg, pady=(theme.spacing.md, theme.spacing.sm))
        ctk.CTkLabel(head, text="Asset Packs — transitions & SFX",
                     font=get_font("md", "bold"), text_color=theme.colors.text_primary).pack(side="left")
        ctk.CTkLabel(
            card,
            text="Point at folders where your DaVinci transition / SFX packs live "
                 "(local drive, external disk, or a synced cloud folder).",
            font=get_font("xs"), text_color=theme.colors.text_muted, wraplength=560, justify="left",
        ).pack(anchor="w", padx=theme.spacing.lg)

        self.packs_list = ctk.CTkFrame(card, fg_color="transparent")
        self.packs_list.pack(fill="x", padx=theme.spacing.lg, pady=theme.spacing.sm)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.md))
        for label, kind in [("➕ Add Transitions Folder", "transition"),
                            ("➕ Add SFX Folder", "sfx"),
                            ("➕ Add Folder (auto)", "auto")]:
            ctk.CTkButton(
                btns, text=label, font=get_font("xs"), height=30,
                command=lambda k=kind: self._add_pack_folder(k),
                **theme.get_button_style("secondary"),
            ).pack(side="left", padx=(0, theme.spacing.xs))

        self._refresh_packs_list()

    def _refresh_packs_list(self):
        for child in self.packs_list.winfo_children():
            child.destroy()
        folders = self.pack_mgr.folders()
        if not folders:
            ctk.CTkLabel(self.packs_list, text="No folders added yet.",
                         font=get_font("xs"), text_color=theme.colors.text_muted).pack(anchor="w")
            return
        for pack in self.pack_mgr.packs():
            row = ctk.CTkFrame(self.packs_list, fg_color="transparent")
            row.pack(fill="x", pady=2)
            status = "🟢" if pack.available else "🔴 offline"
            count = f"{len(pack.items)} files" if pack.available else "unavailable"
            ctk.CTkLabel(
                row, text=f"{status}  {pack.name}  ({pack.kind}, {count})",
                font=get_font("xs"), text_color=theme.colors.text_secondary,
            ).pack(side="left")
            ctk.CTkButton(
                row, text="Remove", font=get_font("xs"), width=64, height=24,
                command=lambda p=str(pack.root): self._remove_pack_folder(p),
                **theme.get_button_style("danger"),
            ).pack(side="right")

    def _add_pack_folder(self, kind: str):
        folder = filedialog.askdirectory(title="Select asset pack folder")
        if not folder:
            return
        self.pack_mgr.add_folder(folder, kind=kind)
        self._refresh_packs_list()
        self._refresh_pack_combos()
        if self.on_status_change:
            self.on_status_change("Asset pack folder added", "success")

    def _remove_pack_folder(self, path: str):
        self.pack_mgr.remove_folder(path)
        self._refresh_packs_list()
        self._refresh_pack_combos()

    def _refresh_pack_combos(self):
        self.transition_combo.configure(values=self._pack_choices("transition"))
        self.sfx_combo.configure(values=self._pack_choices("sfx"))

    # ---- Data binding ------------------------------------------------------

    def _select(self, name: str):
        tpl = self.manager.get(name)
        if tpl is None:
            return
        self.current = tpl
        for n, btn in self._list_buttons.items():
            active = n == name
            btn.configure(fg_color=theme.colors.accent_primary if active else "transparent",
                          hover_color=theme.colors.accent_hover if active else theme.colors.bg_hover)
        self._load_into_form(tpl)
        self.delete_btn.configure(state="disabled" if tpl.builtin else "normal")

    def _load_into_form(self, tpl: ChannelTemplate):
        self.name_var.set(tpl.name)
        self.niche_var.set(tpl.niche)
        self.desc_var.set(tpl.description)
        self.clip_dur_var.set(str(tpl.clip_duration))
        self.min_dur_var.set(str(tpl.min_duration))
        self.max_dur_var.set(str(tpl.max_duration))
        self.max_clips_var.set(str(tpl.max_clips))
        self._set_box(self.hook_phrases_box, "\n".join(tpl.hook_phrases))
        self._set_box(self.hook_words_box, "\n".join(tpl.hook_words))
        for field in WEIGHT_FIELDS:
            self.weight_vars[field].set(str(getattr(tpl.scoring_weights, field)))
        self.persona_var.set(tpl.voice.persona)
        self.tone_var.set(tpl.voice.tone)
        self.title_style_var.set(tpl.voice.title_style)
        self.cta_var.set(tpl.voice.cta)
        self._set_box(self.hashtags_box, " ".join(tpl.voice.hashtag_sets))
        self._set_box(self.keyword_tags_box, "\n".join(tpl.voice.keyword_tags))
        self.caption_var.set(tpl.look.caption_preset)
        self.lut_var.set(tpl.look.lut_name or "")
        self.transition_pack_var.set(tpl.look.transition_pack or "")
        self.sfx_pack_var.set(tpl.look.sfx_pack or "")
        self.auto_trans_var.set(tpl.look.auto_transitions)

    def _set_box(self, box: ctk.CTkTextbox, text: str):
        box.delete("1.0", "end")
        box.insert("1.0", text)

    def _read_box_lines(self, box: ctk.CTkTextbox) -> list[str]:
        raw = box.get("1.0", "end").strip()
        items: list[str] = []
        for line in raw.replace(",", "\n").splitlines():
            val = line.strip()
            if val and val not in items:
                items.append(val)
        return items

    def _form_to_template(self) -> Optional[ChannelTemplate]:
        try:
            weights = ScoringWeightsModel(
                **{f: float(self.weight_vars[f].get() or 0) for f in WEIGHT_FIELDS}
            )
            voice = VoiceProfile(
                persona=self.persona_var.get().strip(),
                tone=self.tone_var.get().strip(),
                title_style=self.title_style_var.get().strip(),
                cta=self.cta_var.get().strip(),
                hashtag_sets=self._read_box_lines(self.hashtags_box),
                keyword_tags=self._read_box_lines(self.keyword_tags_box),
            )
            look = LookAndSound(
                caption_preset=self.caption_var.get(),
                lut_name=self.lut_var.get().strip() or None,
                transition_pack=self.transition_pack_var.get().strip() or None,
                sfx_pack=self.sfx_pack_var.get().strip() or None,
                auto_transitions=bool(self.auto_trans_var.get()),
            )
            return ChannelTemplate(
                name=self.name_var.get().strip() or "Untitled",
                niche=self.niche_var.get().strip() or "general",
                icon=self.current.icon if self.current else "🎬",
                description=self.desc_var.get().strip(),
                content_type=self.current.content_type if self.current else "clips",
                clip_duration=float(self.clip_dur_var.get() or 30),
                min_duration=float(self.min_dur_var.get() or 8),
                max_duration=float(self.max_dur_var.get() or 60),
                max_clips=int(float(self.max_clips_var.get() or 10)),
                hook_phrases=self._read_box_lines(self.hook_phrases_box),
                hook_words=self._read_box_lines(self.hook_words_box),
                scoring_weights=weights,
                voice=voice,
                look=look,
                platforms=self.current.platforms if self.current else ["youtube_shorts"],
            )
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Invalid template", f"Could not read form values:\n{exc}")
            return None

    # ---- Actions -----------------------------------------------------------

    def _save(self):
        tpl = self._form_to_template()
        if tpl is None:
            return
        # Saving a built-in under the same name creates a custom copy.
        existing = self.manager.get(tpl.name)
        if existing is not None and existing.builtin and tpl.name == existing.name:
            tpl.name = f"{tpl.name} (Custom)"
        self.manager.save(tpl)
        self.manager.reload()
        self._refresh_list()
        self._select(tpl.name)
        if self.on_status_change:
            self.on_status_change(f"Saved template '{tpl.name}'", "success")

    def _delete(self):
        if self.current is None or self.current.builtin:
            return
        if not messagebox.askyesno("Delete template", f"Delete '{self.current.name}'?"):
            return
        self.manager.delete(self.current.name)
        self.manager.reload()
        self._refresh_list()
        names = self.manager.names()
        if names:
            self._select(names[0])

    def _export(self):
        if self.current is None:
            return
        dest = filedialog.asksaveasfilename(
            title="Export template", defaultextension=".json",
            initialfile=f"{self.current.slug}.json",
            filetypes=[("Template JSON", "*.json")],
        )
        if dest and self.manager.export(self.current.name, Path(dest)):
            if self.on_status_change:
                self.on_status_change(f"Exported '{self.current.name}'", "success")

    def _import(self):
        src = filedialog.askopenfilename(
            title="Import template", filetypes=[("Template JSON", "*.json")],
        )
        if not src:
            return
        tpl = self.manager.import_file(Path(src))
        if tpl is None:
            messagebox.showerror("Import failed", "That file is not a valid template.")
            return
        self.manager.reload()
        self._refresh_list()
        self._select(tpl.name)

    def _apply(self):
        tpl = self._form_to_template()
        if tpl is None:
            return
        if self.on_apply_template:
            self.on_apply_template(tpl)
        if self.on_status_change:
            self.on_status_change(f"Template '{tpl.name}' ready in Opus Clip AI", "info")
