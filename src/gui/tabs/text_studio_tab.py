"""Text Studio — Remotion-style caption style editor with live preview."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk

from ..theme import get_font, theme
from ...core.captions.models import CaptionStyleModel, TextOverlayModel
from ...core.captions.preview import render_style_preview
from ...core.captions.style_manager import StyleManager

FONTS = ["Arial Black", "Impact", "Helvetica", "Montserrat", "Arial", "Verdana"]
ALIGNMENT_LABELS = {
    7: "Top Left", 8: "Top Center", 9: "Top Right",
    4: "Mid Left", 5: "Mid Center", 6: "Mid Right",
    1: "Bot Left", 2: "Bot Center", 3: "Bot Right",
}
OVERLAY_KINDS = ["title", "watermark", "cta", "custom"]


class TextStudioTab(ctk.CTkFrame):
    """Edit caption styles and text overlays with a live ffmpeg preview."""

    def __init__(
        self,
        parent,
        on_status_change: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_status_change = on_status_change
        self.manager = StyleManager()
        self.current: Optional[CaptionStyleModel] = None
        self._overlays: list[TextOverlayModel] = []
        self._list_buttons: dict[str, ctk.CTkButton] = {}
        self._preview_image: ctk.CTkImage | None = None
        self._preview_job: int | None = None
        self._preview_thread: threading.Thread | None = None
        self._rgb_vars: dict[str, tuple[ctk.StringVar, ctk.CTkButton]] = {}
        self._create_widgets()
        names = self.manager.names()
        if names:
            self._select(names[0])

    # ---- Layout ------------------------------------------------------------

    def _create_widgets(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.sm))
        ctk.CTkLabel(
            header, text="✏️  Text Studio",
            font=get_font("2xl", "bold"), text_color=theme.colors.text_primary,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Design caption styles with opacity, fades, and overlays — live preview.",
            font=get_font("md"), text_color=theme.colors.text_secondary,
        ).pack(anchor="w", pady=(theme.spacing.xs, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=theme.spacing.lg, pady=theme.spacing.md)

        # Left: style list
        left = ctk.CTkFrame(body, fg_color=theme.colors.bg_secondary,
                            corner_radius=theme.spacing.card_radius, width=220)
        left.pack(side="left", fill="y", padx=(0, theme.spacing.md))
        left.pack_propagate(False)
        ctk.CTkLabel(
            left, text="STYLES", font=get_font("xs", "bold"),
            text_color=theme.colors.text_muted,
        ).pack(anchor="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm))
        self.list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=theme.spacing.sm)
        for label, cmd in [
            ("📥  Import…", self._import),
            ("📋  Duplicate", self._duplicate),
        ]:
            ctk.CTkButton(
                left, text=label, font=get_font("xs"), height=30,
                command=cmd, **theme.get_button_style("secondary"),
            ).pack(fill="x", padx=theme.spacing.md, pady=2)
        ctk.CTkButton(
            left, text="➕  New Style", font=get_font("xs"), height=30,
            command=self._new_style, **theme.get_button_style("primary"),
        ).pack(fill="x", padx=theme.spacing.md, pady=(2, theme.spacing.md))

        # Center: editor
        self.editor = ctk.CTkScrollableFrame(body, fg_color="transparent")
        self.editor.pack(side="left", fill="both", expand=True, padx=(0, theme.spacing.md))
        self._build_editor()

        # Right: preview
        right = ctk.CTkFrame(body, fg_color=theme.colors.bg_secondary,
                             corner_radius=theme.spacing.card_radius, width=280)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        ctk.CTkLabel(
            right, text="LIVE PREVIEW", font=get_font("xs", "bold"),
            text_color=theme.colors.text_muted,
        ).pack(anchor="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.sm))
        self.preview_label = ctk.CTkLabel(
            right, text="", width=240, height=420,
            fg_color=theme.colors.bg_tertiary, corner_radius=8,
        )
        self.preview_label.pack(padx=theme.spacing.md, pady=theme.spacing.sm)
        self.preview_status = ctk.CTkLabel(
            right, text="Adjust controls to preview.",
            font=get_font("xs"), text_color=theme.colors.text_muted, wraplength=240,
        )
        self.preview_status.pack(anchor="w", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        ctk.CTkButton(
            right, text="↻  Refresh Preview", font=get_font("xs"), height=32,
            command=self._schedule_preview, **theme.get_button_style("secondary"),
        ).pack(fill="x", padx=theme.spacing.md, pady=(0, theme.spacing.md))

        self._refresh_list()

    def _build_editor(self) -> None:
        e = self.editor
        ident = self._card(e, "Style Identity")
        self.name_var = ctk.StringVar()
        self.font_var = ctk.StringVar(value="Arial Black")
        self._labeled_entry(ident, "Style Name", self.name_var)
        ctk.CTkLabel(ident, text="Font", font=get_font("sm"),
                     text_color=theme.colors.text_secondary).pack(anchor="w")
        ctk.CTkOptionMenu(
            ident, values=FONTS, variable=self.font_var, font=get_font("sm"),
            fg_color=theme.colors.bg_tertiary, button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary,
            command=lambda _: self._on_change(),
        ).pack(fill="x", pady=(theme.spacing.xs, theme.spacing.md))

        typo = self._card(e, "Typography & Colors")
        self.font_size_var = ctk.IntVar(value=64)
        self.outline_px_var = ctk.IntVar(value=6)
        self.shadow_px_var = ctk.IntVar(value=0)
        self._slider_row(typo, "Font size", self.font_size_var, 24, 96)
        self._slider_row(typo, "Outline (px)", self.outline_px_var, 0, 12)
        self._slider_row(typo, "Shadow (px)", self.shadow_px_var, 0, 8)
        self.bold_var = ctk.BooleanVar(value=True)
        self.italic_var = ctk.BooleanVar(value=False)
        self.uppercase_var = ctk.BooleanVar(value=True)
        self.highlight_pop_var = ctk.BooleanVar(value=True)
        toggles = ctk.CTkFrame(typo, fg_color="transparent")
        toggles.pack(fill="x")
        for text, var in [
            ("Bold", self.bold_var), ("Italic", self.italic_var),
            ("Uppercase", self.uppercase_var), ("Word pop", self.highlight_pop_var),
        ]:
            ctk.CTkCheckBox(
                toggles, text=text, variable=var, font=get_font("xs"),
                fg_color=theme.colors.accent_primary,
                command=self._on_change,
            ).pack(side="left", padx=(0, theme.spacing.sm))

        colors = self._card(e, "Colors & Opacity")
        for key, label in [
            ("primary", "Text"), ("highlight", "Highlight"),
            ("outline", "Outline"), ("back", "Background"),
        ]:
            self._color_row(colors, key, label)
        self.primary_opacity_var = ctk.IntVar(value=100)
        self.highlight_opacity_var = ctk.IntVar(value=100)
        self.outline_opacity_var = ctk.IntVar(value=100)
        self.back_opacity_var = ctk.IntVar(value=0)
        for label, var in [
            ("Text opacity", self.primary_opacity_var),
            ("Highlight opacity", self.highlight_opacity_var),
            ("Outline opacity", self.outline_opacity_var),
            ("Box opacity", self.back_opacity_var),
        ]:
            self._slider_row(colors, label, var, 0, 100)

        motion = self._card(e, "Motion & Position")
        self.fade_in_var = ctk.IntVar(value=0)
        self.fade_out_var = ctk.IntVar(value=0)
        self.highlight_scale_var = ctk.IntVar(value=110)
        self.margin_h_var = ctk.IntVar(value=40)
        self.margin_v_var = ctk.IntVar(value=220)
        self._slider_row(motion, "Fade in (ms)", self.fade_in_var, 0, 1000)
        self._slider_row(motion, "Fade out (ms)", self.fade_out_var, 0, 1000)
        self._slider_row(motion, "Pop scale (%)", self.highlight_scale_var, 100, 150)
        self._slider_row(motion, "Margin H", self.margin_h_var, 0, 200)
        self._slider_row(motion, "Margin V", self.margin_v_var, 0, 400)
        ctk.CTkLabel(motion, text="Alignment (9-grid)", font=get_font("sm"),
                     text_color=theme.colors.text_secondary).pack(anchor="w")
        self.alignment_var = ctk.IntVar(value=2)
        grid = ctk.CTkFrame(motion, fg_color="transparent")
        grid.pack(fill="x", pady=(theme.spacing.xs, theme.spacing.md))
        for row_vals in [(7, 8, 9), (4, 5, 6), (1, 2, 3)]:
            row = ctk.CTkFrame(grid, fg_color="transparent")
            row.pack()
            for val in row_vals:
                ctk.CTkRadioButton(
                    row, text="", variable=self.alignment_var, value=val, width=28,
                    fg_color=theme.colors.accent_primary,
                    command=self._on_change,
                ).pack(side="left", padx=2, pady=2)

        overlays_card = self._card(e, "Text Overlays")
        ctk.CTkLabel(
            overlays_card,
            text="Add title cards, watermarks, or CTAs. Use {title} and {channel} tokens.",
            font=get_font("xs"), text_color=theme.colors.text_muted, wraplength=500,
        ).pack(anchor="w", pady=(0, theme.spacing.sm))
        self.overlays_frame = ctk.CTkFrame(overlays_card, fg_color="transparent")
        self.overlays_frame.pack(fill="x")
        ctk.CTkButton(
            overlays_card, text="➕  Add Overlay", font=get_font("xs"), height=30,
            command=self._add_overlay, **theme.get_button_style("secondary"),
        ).pack(anchor="w", pady=(theme.spacing.sm, 0))

        actions = ctk.CTkFrame(e, fg_color="transparent")
        actions.pack(fill="x", pady=theme.spacing.lg)
        row = ctk.CTkFrame(actions, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkButton(
            row, text="💾  Save", font=get_font("sm"), height=36,
            command=self._save, **theme.get_button_style("primary"),
        ).pack(side="left", fill="x", expand=True, padx=(0, theme.spacing.xs))
        ctk.CTkButton(
            row, text="📤  Export", font=get_font("sm"), height=36,
            command=self._export, **theme.get_button_style("secondary"),
        ).pack(side="left", fill="x", expand=True, padx=theme.spacing.xs)
        self.delete_btn = ctk.CTkButton(
            row, text="🗑️  Delete", font=get_font("sm"), height=36,
            command=self._delete, **theme.get_button_style("danger"),
        )
        self.delete_btn.pack(side="left", fill="x", expand=True, padx=(theme.spacing.xs, 0))

    # ---- Widget helpers ----------------------------------------------------

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

    def _labeled_entry(self, parent, label: str, var: ctk.StringVar) -> None:
        ctk.CTkLabel(parent, text=label, font=get_font("sm"),
                     text_color=theme.colors.text_secondary).pack(anchor="w")
        entry = ctk.CTkEntry(parent, textvariable=var, font=get_font("sm"),
                             **theme.get_input_style())
        entry.pack(fill="x", pady=(theme.spacing.xs, theme.spacing.md))
        entry.bind("<KeyRelease>", lambda _: self._on_change())

    def _slider_row(self, parent, label: str, var: ctk.IntVar, lo: int, hi: int) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, font=get_font("xs"),
                     text_color=theme.colors.text_secondary, width=120).pack(side="left")
        val_lbl = ctk.CTkLabel(row, text=str(var.get()), font=get_font("xs"),
                               text_color=theme.colors.text_muted, width=36)
        val_lbl.pack(side="right")
        ctk.CTkSlider(
            row, from_=lo, to=hi, variable=var, width=200,
            fg_color=theme.colors.bg_tertiary,
            progress_color=theme.colors.accent_primary,
            button_color=theme.colors.accent_primary,
            command=lambda v, lbl=val_lbl: (lbl.configure(text=str(int(float(v)))), self._on_change()),
        ).pack(side="left", fill="x", expand=True, padx=(theme.spacing.xs, theme.spacing.sm))

    def _color_row(self, parent, key: str, label: str) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, font=get_font("xs"),
                     text_color=theme.colors.text_secondary, width=90).pack(side="left")
        hex_var = ctk.StringVar(value="#ffffff")
        self._rgb_vars[key] = (hex_var, ctk.CTkButton(
            row, text="", width=36, height=24,
            fg_color="#ffffff", hover_color="#cccccc",
            command=lambda k=key: self._pick_color(k),
        ))
        self._rgb_vars[key][1].pack(side="left", padx=(0, theme.spacing.sm))
        ctk.CTkEntry(row, textvariable=hex_var, width=90, font=get_font("xs", mono=True),
                     **theme.get_input_style()).pack(side="left")
        hex_var.trace_add("write", lambda *_: self._on_change())

    def _pick_color(self, key: str) -> None:
        hex_var, btn = self._rgb_vars[key]
        result = colorchooser.askcolor(color=hex_var.get(), title=f"Pick {key} color")
        if result and result[1]:
            hex_var.set(result[1])
            btn.configure(fg_color=result[1])

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return (255, 255, 255)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def _rgb_to_hex(self, rgb: tuple[int, int, int]) -> str:
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    # ---- Data binding ------------------------------------------------------

    def _refresh_list(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        self._list_buttons.clear()
        for style in self.manager.all():
            label = style.name + ("" if style.builtin else "  •")
            btn = ctk.CTkButton(
                self.list_frame, text=label, font=get_font("sm"),
                height=34, anchor="w",
                fg_color="transparent", hover_color=theme.colors.bg_hover,
                command=lambda n=style.name: self._select(n),
            )
            btn.pack(fill="x", pady=1)
            self._list_buttons[style.name] = btn

    def _select(self, name: str) -> None:
        style = self.manager.get(name)
        if style is None:
            return
        self.current = style
        for n, btn in self._list_buttons.items():
            active = n == name
            btn.configure(
                fg_color=theme.colors.accent_primary if active else "transparent",
                hover_color=theme.colors.accent_hover if active else theme.colors.bg_hover,
            )
        self._load_into_form(style)
        self.delete_btn.configure(state="disabled" if style.builtin else "normal")
        self._schedule_preview()

    def _load_into_form(self, style: CaptionStyleModel) -> None:
        self.name_var.set(style.name)
        self.font_var.set(style.font)
        self.font_size_var.set(style.font_size)
        self.outline_px_var.set(style.outline_px)
        self.shadow_px_var.set(style.shadow_px)
        self.bold_var.set(style.bold)
        self.italic_var.set(style.italic)
        self.uppercase_var.set(style.uppercase)
        self.highlight_pop_var.set(style.highlight_pop)
        self.primary_opacity_var.set(style.primary_opacity)
        self.highlight_opacity_var.set(style.highlight_opacity)
        self.outline_opacity_var.set(style.outline_opacity)
        self.back_opacity_var.set(style.back_opacity)
        self.fade_in_var.set(style.fade_in_ms)
        self.fade_out_var.set(style.fade_out_ms)
        self.highlight_scale_var.set(style.highlight_scale)
        self.margin_h_var.set(style.margin_h)
        self.margin_v_var.set(style.margin_v)
        self.alignment_var.set(style.alignment)
        for key, rgb in [
            ("primary", style.primary_rgb), ("highlight", style.highlight_rgb),
            ("outline", style.outline_rgb), ("back", style.back_rgb),
        ]:
            hex_var, btn = self._rgb_vars[key]
            hex_val = self._rgb_to_hex(rgb)
            hex_var.set(hex_val)
            btn.configure(fg_color=hex_val)
        self._overlays = []
        self._refresh_overlays_ui()

    def _form_to_style(self) -> Optional[CaptionStyleModel]:
        try:
            return CaptionStyleModel(
                name=self.name_var.get().strip() or "Untitled",
                font=self.font_var.get(),
                font_size=int(self.font_size_var.get()),
                primary_rgb=self._hex_to_rgb(self._rgb_vars["primary"][0].get()),
                highlight_rgb=self._hex_to_rgb(self._rgb_vars["highlight"][0].get()),
                outline_rgb=self._hex_to_rgb(self._rgb_vars["outline"][0].get()),
                back_rgb=self._hex_to_rgb(self._rgb_vars["back"][0].get()),
                outline_px=int(self.outline_px_var.get()),
                shadow_px=int(self.shadow_px_var.get()),
                bold=bool(self.bold_var.get()),
                italic=bool(self.italic_var.get()),
                uppercase=bool(self.uppercase_var.get()),
                highlight_pop=bool(self.highlight_pop_var.get()),
                primary_opacity=int(self.primary_opacity_var.get()),
                highlight_opacity=int(self.highlight_opacity_var.get()),
                outline_opacity=int(self.outline_opacity_var.get()),
                back_opacity=int(self.back_opacity_var.get()),
                fade_in_ms=int(self.fade_in_var.get()),
                fade_out_ms=int(self.fade_out_var.get()),
                highlight_scale=int(self.highlight_scale_var.get()),
                alignment=int(self.alignment_var.get()),
                margin_h=int(self.margin_h_var.get()),
                margin_v=int(self.margin_v_var.get()),
                bottom_margin_px=int(self.margin_v_var.get()),
                builtin=self.current.builtin if self.current else False,
            )
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Invalid style", str(exc))
            return None

    # ---- Overlays ----------------------------------------------------------

    def _refresh_overlays_ui(self) -> None:
        for child in self.overlays_frame.winfo_children():
            child.destroy()
        for idx, overlay in enumerate(self._overlays):
            row = ctk.CTkFrame(self.overlays_frame, fg_color=theme.colors.bg_tertiary,
                               corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                row, text=f"{overlay.kind}: {overlay.text[:40]}",
                font=get_font("xs"), text_color=theme.colors.text_secondary,
            ).pack(side="left", padx=theme.spacing.sm, pady=theme.spacing.xs)
            ctk.CTkButton(
                row, text="✕", width=28, height=24, font=get_font("xs"),
                command=lambda i=idx: self._remove_overlay(i),
                **theme.get_button_style("danger"),
            ).pack(side="right", padx=theme.spacing.sm)

    def _add_overlay(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Text Overlay")
        dialog.geometry("400x320")
        dialog.transient(self.winfo_toplevel())
        text_var = ctk.StringVar(value="{title}")
        kind_var = ctk.StringVar(value="title")
        align_var = ctk.IntVar(value=8)
        fade_in_var = ctk.IntVar(value=300)
        fade_out_var = ctk.IntVar(value=300)

        ctk.CTkLabel(dialog, text="Text", font=get_font("sm")).pack(anchor="w", padx=16, pady=(12, 0))
        ctk.CTkEntry(dialog, textvariable=text_var, font=get_font("sm")).pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(dialog, text="Kind", font=get_font("sm")).pack(anchor="w", padx=16)
        ctk.CTkOptionMenu(dialog, values=OVERLAY_KINDS, variable=kind_var).pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(dialog, text="Alignment", font=get_font("sm")).pack(anchor="w", padx=16)
        ctk.CTkOptionMenu(
            dialog,
            values=[f"{k} — {v}" for k, v in ALIGNMENT_LABELS.items()],
            command=lambda v: align_var.set(int(v.split(" — ")[0])),
        ).pack(fill="x", padx=16, pady=4)

        def confirm() -> None:
            self._overlays.append(TextOverlayModel(
                text=text_var.get().strip() or "Overlay",
                kind=kind_var.get(),  # type: ignore[arg-type]
                alignment=align_var.get(),
                fade_in_ms=fade_in_var.get(),
                fade_out_ms=fade_out_var.get(),
            ))
            self._refresh_overlays_ui()
            self._schedule_preview()
            dialog.destroy()

        ctk.CTkButton(dialog, text="Add", command=confirm,
                      **theme.get_button_style("primary")).pack(pady=16)

    def _remove_overlay(self, idx: int) -> None:
        if 0 <= idx < len(self._overlays):
            self._overlays.pop(idx)
            self._refresh_overlays_ui()
            self._schedule_preview()

    # ---- Preview -----------------------------------------------------------

    def _on_change(self) -> None:
        self._schedule_preview()

    def _schedule_preview(self) -> None:
        if self._preview_job is not None:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(600, self._run_preview)

    def _run_preview(self) -> None:
        self._preview_job = None
        style = self._form_to_style()
        if style is None:
            return
        if self._preview_thread and self._preview_thread.is_alive():
            return
        self.preview_status.configure(text="Rendering preview…")
        overlays = list(self._overlays)
        out_dir = Path(__file__).resolve().parents[3] / "assets" / "preview"
        out_path = out_dir / f"studio_{style.slug}.jpg"

        def work() -> None:
            try:
                render_style_preview(
                    style, out_path,
                    overlays=overlays,
                    overlay_metadata={"title": "Your Clip Title", "channel": "My Channel"},
                )
                self.after(0, lambda: self._show_preview(out_path))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self.preview_status.configure(text=f"Preview failed: {exc}"))

        self._preview_thread = threading.Thread(target=work, daemon=True)
        self._preview_thread.start()

    def _show_preview(self, path: Path) -> None:
        try:
            self._preview_image = ctk.CTkImage(
                light_image=str(path), dark_image=str(path), size=(240, 420),
            )
            self.preview_label.configure(image=self._preview_image, text="")
            self.preview_status.configure(text=f"Preview saved: {path.name}")
        except Exception as exc:
            self.preview_status.configure(text=f"Could not display: {exc}")

    # ---- Actions -----------------------------------------------------------

    def _save(self) -> None:
        style = self._form_to_style()
        if style is None:
            return
        if self.current and self.current.builtin and style.name == self.current.name:
            style.name = f"{style.name} (Custom)"
        self.manager.save(style)
        self.manager.reload()
        self._refresh_list()
        self._select(style.name)
        if self.on_status_change:
            self.on_status_change(f"Saved style '{style.name}'", "success")

    def _delete(self) -> None:
        if self.current is None or self.current.builtin:
            return
        if not messagebox.askyesno("Delete style", f"Delete '{self.current.name}'?"):
            return
        self.manager.delete(self.current.name)
        self.manager.reload()
        self._refresh_list()
        names = self.manager.names()
        if names:
            self._select(names[0])

    def _export(self) -> None:
        if self.current is None:
            return
        dest = filedialog.asksaveasfilename(
            title="Export caption style", defaultextension=".json",
            initialfile=f"{self.current.slug}.json",
            filetypes=[("Caption Style JSON", "*.json")],
        )
        if dest and self.manager.export(self.current.name, Path(dest)):
            if self.on_status_change:
                self.on_status_change(f"Exported '{self.current.name}'", "success")

    def _import(self) -> None:
        src = filedialog.askopenfilename(
            title="Import caption style", filetypes=[("Caption Style JSON", "*.json")],
        )
        if not src:
            return
        style = self.manager.import_file(Path(src))
        if style is None:
            messagebox.showerror("Import failed", "That file is not a valid caption style.")
            return
        self.manager.reload()
        self._refresh_list()
        self._select(style.name)

    def _duplicate(self) -> None:
        if self.current is None:
            return
        new_name = f"{self.current.name} Copy"
        dup = self.manager.duplicate(self.current.name, new_name)
        if dup:
            self.manager.reload()
            self._refresh_list()
            self._select(dup.name)

    def _new_style(self) -> None:
        base = self._form_to_style() or CaptionStyleModel(name="New Style")
        base.name = "New Style"
        base.builtin = False
        self.current = base
        self._load_into_form(base)
        self._schedule_preview()

    def style_names(self) -> list[str]:
        return self.manager.names()
