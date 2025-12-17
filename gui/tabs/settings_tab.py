"""
LTW Video Editor Pro - Settings Tab
Presets and configuration management
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from typing import Callable, Optional, List, Dict, Any
from pathlib import Path
import json
import sys
import os

from ..theme import theme, get_font
from ..utils.preset_manager import PresetManager, Preset


class PresetCard(ctk.CTkFrame):
    """Card displaying a preset"""
    
    def __init__(self, parent, preset: Preset, on_apply: Optional[Callable] = None,
                 on_delete: Optional[Callable] = None, **kwargs):
        super().__init__(
            parent,
            fg_color=theme.colors.bg_tertiary,
            corner_radius=8,
            cursor="hand2",
            **kwargs
        )
        
        self.preset = preset
        self.on_apply = on_apply
        self.on_delete = on_delete
        
        self.bind("<Button-1>", lambda e: self._on_apply())
        self._create_widgets()
        
    def _create_widgets(self):
        """Create card widgets"""
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=theme.spacing.md, pady=theme.spacing.md)
        content.bind("<Button-1>", lambda e: self._on_apply())
        
        # Header row
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x")
        header.bind("<Button-1>", lambda e: self._on_apply())
        
        # Category badge
        category_colors = {
            "sports": "#ff6b35",
            "educational": "#00b4d8",
            "general": "#6b7280",
            "social": "#9b5de5",
            "gaming": "#10b981",
            "film": "#f59e0b",
            "custom": theme.colors.accent_primary
        }
        
        badge = ctk.CTkLabel(
            header,
            text=self.preset.category.upper(),
            font=get_font("xs"),
            text_color=theme.colors.text_primary,
            fg_color=category_colors.get(self.preset.category, theme.colors.accent_primary),
            corner_radius=4,
            padx=6,
            pady=2
        )
        badge.pack(side="left")
        badge.bind("<Button-1>", lambda e: self._on_apply())
        
        # Delete button (only for custom presets)
        if self.preset.category == "custom" and self.on_delete:
            del_btn = ctk.CTkButton(
                header,
                text="✕",
                font=get_font("xs"),
                width=24,
                height=24,
                fg_color="transparent",
                hover_color=theme.colors.error,
                text_color=theme.colors.text_muted,
                command=self._on_delete
            )
            del_btn.pack(side="right")
        
        # Name
        name_label = ctk.CTkLabel(
            content,
            text=self.preset.name,
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary,
            anchor="w"
        )
        name_label.pack(anchor="w", pady=(theme.spacing.sm, 0))
        name_label.bind("<Button-1>", lambda e: self._on_apply())
        
        # Description
        if self.preset.description:
            desc_label = ctk.CTkLabel(
                content,
                text=self.preset.description,
                font=get_font("xs"),
                text_color=theme.colors.text_muted,
                anchor="w",
                wraplength=250
            )
            desc_label.pack(anchor="w")
            desc_label.bind("<Button-1>", lambda e: self._on_apply())
        
        # Settings preview
        settings_text = f"{self.preset.clip_duration}s • {self.preset.quality}"
        if self.preset.scene_detection:
            settings_text += " • Scene Detection"
            
        settings_label = ctk.CTkLabel(
            content,
            text=settings_text,
            font=get_font("xs"),
            text_color=theme.colors.text_muted,
            anchor="w"
        )
        settings_label.pack(anchor="w", pady=(theme.spacing.xs, 0))
        settings_label.bind("<Button-1>", lambda e: self._on_apply())
        
    def _on_apply(self):
        """Handle apply click"""
        if self.on_apply:
            self.on_apply(self.preset)
            
    def _on_delete(self):
        """Handle delete click"""
        if self.on_delete:
            if messagebox.askyesno("Delete Preset", f"Delete preset '{self.preset.name}'?"):
                self.on_delete(self.preset.name)


class SettingsTab(ctk.CTkFrame):
    """Settings and presets tab"""
    
    def __init__(self, parent, on_preset_apply: Optional[Callable] = None,
                 get_current_settings: Optional[Callable] = None,
                 on_status_change: Optional[Callable] = None, **kwargs):
        super().__init__(
            parent,
            fg_color="transparent",
            **kwargs
        )
        
        self.on_preset_apply = on_preset_apply
        self.get_current_settings = get_current_settings
        self.on_status_change = on_status_change
        self.preset_manager = PresetManager()
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Create tab widgets"""
        # Scrollable container
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=theme.spacing.lg, pady=theme.spacing.lg)
        
        # Header
        header = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, theme.spacing.xl))
        
        title = ctk.CTkLabel(
            header,
            text="⚙️  Settings & Presets",
            font=get_font("2xl", "bold"),
            text_color=theme.colors.text_primary
        )
        title.pack(anchor="w")
        
        subtitle = ctk.CTkLabel(
            header,
            text="Save and manage your processing configurations",
            font=get_font("md"),
            text_color=theme.colors.text_secondary
        )
        subtitle.pack(anchor="w", pady=(theme.spacing.xs, 0))
        
        # Presets Section
        presets_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius
        )
        presets_card.pack(fill="x", pady=(0, theme.spacing.lg))
        
        presets_header = ctk.CTkFrame(presets_card, fg_color="transparent")
        presets_header.pack(fill="x", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.md))
        
        presets_title = ctk.CTkLabel(
            presets_header,
            text="📋  Presets",
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary
        )
        presets_title.pack(side="left")
        
        # Create preset button
        create_btn = ctk.CTkButton(
            presets_header,
            text="+ Create Preset",
            font=get_font("xs"),
            height=28,
            command=self._create_preset,
            **theme.get_button_style("secondary")
        )
        create_btn.pack(side="right")
        
        # Preset list
        self.presets_frame = ctk.CTkFrame(presets_card, fg_color="transparent")
        self.presets_frame.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        
        self._refresh_presets()
        
        # Import/Export
        ie_frame = ctk.CTkFrame(presets_card, fg_color="transparent")
        ie_frame.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        
        import_btn = ctk.CTkButton(
            ie_frame,
            text="📥 Import Preset",
            font=get_font("xs"),
            height=28,
            command=self._import_preset,
            **theme.get_button_style("ghost")
        )
        import_btn.pack(side="left", padx=(0, theme.spacing.sm))
        
        export_btn = ctk.CTkButton(
            ie_frame,
            text="📤 Export Preset",
            font=get_font("xs"),
            height=28,
            command=self._export_preset,
            **theme.get_button_style("ghost")
        )
        export_btn.pack(side="left")
        
        # Default Settings
        defaults_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius
        )
        defaults_card.pack(fill="x", pady=(0, theme.spacing.lg))
        
        defaults_title = ctk.CTkLabel(
            defaults_card,
            text="🔧  Default Settings",
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary
        )
        defaults_title.pack(anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.md))
        
        defaults_content = ctk.CTkFrame(defaults_card, fg_color="transparent")
        defaults_content.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        
        # Default output directory
        output_frame = ctk.CTkFrame(defaults_content, fg_color="transparent")
        output_frame.pack(fill="x", pady=(0, theme.spacing.md))
        
        output_label = ctk.CTkLabel(
            output_frame,
            text="Default Output Directory",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        output_label.pack(anchor="w")
        
        output_control = ctk.CTkFrame(output_frame, fg_color="transparent")
        output_control.pack(fill="x", pady=(theme.spacing.xs, 0))
        
        self.default_output_var = ctk.StringVar(value=str(Path.home() / "Desktop" / "clips"))
        output_entry = ctk.CTkEntry(
            output_control,
            textvariable=self.default_output_var,
            font=get_font("sm"),
            **theme.get_input_style()
        )
        output_entry.pack(side="left", fill="x", expand=True, padx=(0, theme.spacing.sm))
        
        output_btn = ctk.CTkButton(
            output_control,
            text="Browse",
            font=get_font("xs"),
            width=60,
            command=self._browse_output,
            **theme.get_button_style("secondary")
        )
        output_btn.pack(side="right")
        
        # Default quality
        quality_frame = ctk.CTkFrame(defaults_content, fg_color="transparent")
        quality_frame.pack(fill="x", pady=(0, theme.spacing.md))
        
        quality_label = ctk.CTkLabel(
            quality_frame,
            text="Default Quality",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        quality_label.pack(anchor="w")
        
        self.default_quality_var = ctk.StringVar(value="youtube_hd")
        quality_menu = ctk.CTkOptionMenu(
            quality_frame,
            values=["youtube_sd", "youtube_hd", "youtube_4k", "original"],
            variable=self.default_quality_var,
            font=get_font("sm"),
            fg_color=theme.colors.bg_tertiary,
            button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary
        )
        quality_menu.pack(anchor="w", pady=(theme.spacing.xs, 0))
        
        # Appearance
        appearance_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius
        )
        appearance_card.pack(fill="x", pady=(0, theme.spacing.lg))
        
        appearance_title = ctk.CTkLabel(
            appearance_card,
            text="🎨  Appearance",
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary
        )
        appearance_title.pack(anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.md))
        
        appearance_content = ctk.CTkFrame(appearance_card, fg_color="transparent")
        appearance_content.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        
        # Theme selector
        theme_label = ctk.CTkLabel(
            appearance_content,
            text="Theme",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        theme_label.pack(anchor="w")
        
        theme_options = ctk.CTkFrame(appearance_content, fg_color="transparent")
        theme_options.pack(anchor="w", pady=(theme.spacing.xs, 0))
        
        self.theme_var = ctk.StringVar(value="dark")
        
        dark_btn = ctk.CTkRadioButton(
            theme_options,
            text="Dark",
            variable=self.theme_var,
            value="dark",
            font=get_font("sm"),
            fg_color=theme.colors.accent_primary
        )
        dark_btn.pack(side="left", padx=(0, theme.spacing.lg))
        
        light_btn = ctk.CTkRadioButton(
            theme_options,
            text="Light",
            variable=self.theme_var,
            value="light",
            font=get_font("sm"),
            fg_color=theme.colors.accent_primary,
            state="disabled"  # Not implemented yet
        )
        light_btn.pack(side="left")
        
        # About Section
        about_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius
        )
        about_card.pack(fill="x")
        
        about_title = ctk.CTkLabel(
            about_card,
            text="ℹ️  About",
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary
        )
        about_title.pack(anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.md))
        
        about_content = ctk.CTkLabel(
            about_card,
            text="LTW Video Editor Pro v2.0\nProfessional video splitting and editing suite\n\nBuilt with CustomTkinter\nDaVinci Resolve integration included",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary,
            justify="left"
        )
        about_content.pack(anchor="w", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        
    def _refresh_presets(self):
        """Refresh preset list"""
        # Clear existing
        for widget in self.presets_frame.winfo_children():
            widget.destroy()
            
        # Add presets
        presets = self.preset_manager.get_all_presets()
        
        # Create grid
        row_frame = None
        for i, preset in enumerate(presets):
            if i % 2 == 0:
                row_frame = ctk.CTkFrame(self.presets_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=2)
                
            card = PresetCard(
                row_frame,
                preset=preset,
                on_apply=self._apply_preset,
                on_delete=self._delete_preset
            )
            card.pack(side="left", fill="x", expand=True, padx=(0 if i % 2 == 0 else theme.spacing.sm, 0))
            
    def _apply_preset(self, preset: Preset):
        """Apply a preset"""
        if self.on_preset_apply:
            self.on_preset_apply(preset)
            
        if self.on_status_change:
            self.on_status_change(f"Applied: {preset.name}", "success")
            
        messagebox.showinfo("Preset Applied", f"Applied preset: {preset.name}")
        
    def _delete_preset(self, name: str):
        """Delete a preset"""
        if self.preset_manager.delete_preset(name):
            self._refresh_presets()
            if self.on_status_change:
                self.on_status_change(f"Deleted: {name}", "info")
                
    def _create_preset(self):
        """Create a new preset from current settings"""
        name = simpledialog.askstring("New Preset", "Enter preset name:")
        if not name:
            return
            
        # Get current settings if available
        settings = {}
        if self.get_current_settings:
            settings = self.get_current_settings()
            
        description = simpledialog.askstring("New Preset", "Enter description (optional):") or ""
        
        preset = self.preset_manager.create_preset_from_settings(
            name=name,
            settings=settings,
            category="custom",
            description=description
        )
        
        self._refresh_presets()
        
        if self.on_status_change:
            self.on_status_change(f"Created: {name}", "success")
            
        messagebox.showinfo("Preset Created", f"Created preset: {name}")
        
    def _import_preset(self):
        """Import a preset from file"""
        file = filedialog.askopenfilename(
            title="Import Preset",
            filetypes=[("JSON files", "*.json")]
        )
        
        if file:
            preset = self.preset_manager.import_preset(Path(file))
            if preset:
                self._refresh_presets()
                messagebox.showinfo("Imported", f"Imported preset: {preset.name}")
            else:
                messagebox.showerror("Error", "Failed to import preset")
                
    def _export_preset(self):
        """Export a preset to file"""
        presets = self.preset_manager.get_all_presets()
        preset_names = [p.name for p in presets]
        
        # Simple selection using messagebox (could be improved with custom dialog)
        name = simpledialog.askstring(
            "Export Preset",
            f"Enter preset name to export:\n{', '.join(preset_names)}"
        )
        
        if not name or name not in preset_names:
            return
            
        file = filedialog.asksaveasfilename(
            title="Export Preset",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        
        if file:
            if self.preset_manager.export_preset(name, Path(file)):
                messagebox.showinfo("Exported", f"Exported preset to: {file}")
            else:
                messagebox.showerror("Error", "Failed to export preset")
                
    def _browse_output(self):
        """Browse for default output directory"""
        directory = filedialog.askdirectory(title="Select Default Output Directory")
        if directory:
            self.default_output_var.set(directory)

