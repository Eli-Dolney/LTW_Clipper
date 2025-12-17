"""
LTW Video Editor Pro - DaVinci Resolve Tab
Script management and Resolve integration
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Callable, Optional, List, Dict
from pathlib import Path
import shutil
import sys
import os

from ..theme import theme, get_font


class ScriptCard(ctk.CTkFrame):
    """Card for a Resolve script"""
    
    def __init__(self, parent, name: str, description: str, icon: str,
                 installed: bool = False, on_install: Optional[Callable] = None, **kwargs):
        super().__init__(
            parent,
            fg_color=theme.colors.bg_tertiary,
            corner_radius=8,
            **kwargs
        )
        
        self.name = name
        self.installed = installed
        self.on_install = on_install
        
        self._create_widgets(description, icon)
        
    def _create_widgets(self, description: str, icon: str):
        """Create card widgets"""
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=theme.spacing.md, pady=theme.spacing.md)
        
        # Icon and info
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)
        
        title_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        title_row.pack(anchor="w")
        
        icon_label = ctk.CTkLabel(
            title_row,
            text=icon,
            font=get_font("lg")
        )
        icon_label.pack(side="left", padx=(0, theme.spacing.sm))
        
        name_label = ctk.CTkLabel(
            title_row,
            text=self.name,
            font=get_font("sm", "bold"),
            text_color=theme.colors.text_primary
        )
        name_label.pack(side="left")
        
        if self.installed:
            status_label = ctk.CTkLabel(
                title_row,
                text="✓ Installed",
                font=get_font("xs"),
                text_color=theme.colors.success
            )
            status_label.pack(side="left", padx=(theme.spacing.sm, 0))
        
        desc_label = ctk.CTkLabel(
            info_frame,
            text=description,
            font=get_font("xs"),
            text_color=theme.colors.text_muted,
            anchor="w"
        )
        desc_label.pack(anchor="w", pady=(2, 0))
        
        # Install button
        if not self.installed:
            install_btn = ctk.CTkButton(
                content,
                text="Install",
                font=get_font("xs"),
                width=60,
                height=28,
                command=lambda: self._on_install_click(),
                **theme.get_button_style("secondary")
            )
            install_btn.pack(side="right")
            
    def _on_install_click(self):
        """Handle install click"""
        if self.on_install:
            self.on_install(self.name)


class LUTCard(ctk.CTkFrame):
    """Card for a LUT preview"""
    
    def __init__(self, parent, name: str, preview_color: str, **kwargs):
        super().__init__(
            parent,
            fg_color=theme.colors.bg_tertiary,
            corner_radius=8,
            cursor="hand2",
            **kwargs
        )
        
        self.name = name
        
        # Color preview
        preview = ctk.CTkFrame(
            self,
            fg_color=preview_color,
            height=60,
            corner_radius=8
        )
        preview.pack(fill="x", padx=4, pady=4)
        
        # Name
        name_label = ctk.CTkLabel(
            self,
            text=name,
            font=get_font("xs"),
            text_color=theme.colors.text_secondary
        )
        name_label.pack(pady=(0, 4))


class ResolveTab(ctk.CTkFrame):
    """DaVinci Resolve integration tab"""
    
    def __init__(self, parent, on_status_change: Optional[Callable] = None, **kwargs):
        super().__init__(
            parent,
            fg_color="transparent",
            **kwargs
        )
        
        self.on_status_change = on_status_change
        self.scripts_dir = Path(__file__).parent.parent.parent / "resolve_scripts"
        self.luts_dir = Path(__file__).parent.parent.parent / "assets" / "luts"
        
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
            text="🎭  DaVinci Resolve",
            font=get_font("2xl", "bold"),
            text_color=theme.colors.text_primary
        )
        title.pack(anchor="w")
        
        subtitle = ctk.CTkLabel(
            header,
            text="Automation scripts and integration tools for DaVinci Resolve",
            font=get_font("md"),
            text_color=theme.colors.text_secondary
        )
        subtitle.pack(anchor="w", pady=(theme.spacing.xs, 0))
        
        # Quick Actions
        actions_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius
        )
        actions_card.pack(fill="x", pady=(0, theme.spacing.lg))
        
        actions_title = ctk.CTkLabel(
            actions_card,
            text="⚡  Quick Actions",
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary
        )
        actions_title.pack(anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.md))
        
        actions_grid = ctk.CTkFrame(actions_card, fg_color="transparent")
        actions_grid.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        
        # Install all button
        install_all_btn = ctk.CTkButton(
            actions_grid,
            text="📦  Install All Scripts to Resolve",
            font=get_font("sm", "bold"),
            height=40,
            command=self._install_all_scripts,
            **theme.get_button_style("primary")
        )
        install_all_btn.pack(fill="x", pady=(0, theme.spacing.sm))
        
        # Quick action buttons row
        quick_row = ctk.CTkFrame(actions_grid, fg_color="transparent")
        quick_row.pack(fill="x")
        
        quick_actions = [
            ("📂 Open Scripts Folder", self._open_scripts_folder),
            ("🎨 Open LUTs Folder", self._open_luts_folder),
            ("📋 Copy Import Script", self._copy_import_script)
        ]
        
        for text, command in quick_actions:
            btn = ctk.CTkButton(
                quick_row,
                text=text,
                font=get_font("xs"),
                height=32,
                command=command,
                **theme.get_button_style("secondary")
            )
            btn.pack(side="left", fill="x", expand=True, padx=(0, theme.spacing.xs))
            
        # Scripts Section
        scripts_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius
        )
        scripts_card.pack(fill="x", pady=(0, theme.spacing.lg))
        
        scripts_header = ctk.CTkFrame(scripts_card, fg_color="transparent")
        scripts_header.pack(fill="x", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.md))
        
        scripts_title = ctk.CTkLabel(
            scripts_header,
            text="📜  Available Scripts",
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary
        )
        scripts_title.pack(side="left")
        
        script_count = self._get_script_count()
        count_label = ctk.CTkLabel(
            scripts_header,
            text=f"{script_count} scripts",
            font=get_font("xs"),
            text_color=theme.colors.text_muted
        )
        count_label.pack(side="right")
        
        # Script list
        scripts_list = ctk.CTkFrame(scripts_card, fg_color="transparent")
        scripts_list.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        
        scripts = [
            ("LTW_Universal_Import", "Import any folder of clips with timeline creation", "📥"),
            ("LTW_Add_Transitions", "Add transitions between all clips", "🔀"),
            ("LTW_Apply_Look", "Apply color grading presets and LUTs", "🎨"),
            ("LTW_Project_Setup", "Quick project resolution and frame rate setup", "⚙️"),
            ("LTW_Smart_Fit", "Auto-scale clips to match timeline resolution", "📐"),
            ("LTW_Quick_Render", "One-click render with YouTube/social presets", "🎬"),
            ("LTW_Add_Branding", "Add intros, outros, and branding elements", "🏷️"),
            ("LTW_Import_Beat_Edits", "Create beat-synced timelines from audio", "🎵"),
            ("LTW_Transcript_Importer", "Import SRT/JSON transcripts", "📝"),
            ("LTW_Import_Smart_Clips", "Import AI-selected clips", "🤖"),
            ("LTW_Use_Resolve_Transcription", "Use Resolve Studio's built-in transcription", "🎙️"),
        ]
        
        for name, desc, icon in scripts:
            installed = self._is_script_installed(name)
            card = ScriptCard(
                scripts_list,
                name=name,
                description=desc,
                icon=icon,
                installed=installed,
                on_install=self._install_script
            )
            card.pack(fill="x", pady=2)
            
        # LUTs Section
        luts_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius
        )
        luts_card.pack(fill="x", pady=(0, theme.spacing.lg))
        
        luts_title = ctk.CTkLabel(
            luts_card,
            text="🎨  LUT Gallery",
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary
        )
        luts_title.pack(anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.md))
        
        luts_desc = ctk.CTkLabel(
            luts_card,
            text="Available color grading LUTs",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        luts_desc.pack(anchor="w", padx=theme.spacing.lg)
        
        luts_grid = ctk.CTkFrame(luts_card, fg_color="transparent")
        luts_grid.pack(fill="x", padx=theme.spacing.lg, pady=theme.spacing.lg)
        
        luts = [
            ("Sports Pop", "#ff6b35"),
            ("Cinematic Teal", "#00b4d8"),
            ("Gaming Vibrant", "#9b5de5"),
            ("Tutorial Clean", "#6b7280"),
            ("Warm Sunset", "#f59e0b"),
            ("Cool Night", "#1e40af")
        ]
        
        for name, color in luts:
            card = LUTCard(luts_grid, name=name, preview_color=color)
            card.pack(side="left", padx=(0, theme.spacing.sm))
            
        # Add LUT button
        add_lut_btn = ctk.CTkButton(
            luts_card,
            text="+ Add Custom LUT",
            font=get_font("sm"),
            height=32,
            command=self._add_custom_lut,
            **theme.get_button_style("ghost")
        )
        add_lut_btn.pack(anchor="w", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        
        # Instructions
        help_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius
        )
        help_card.pack(fill="x")
        
        help_title = ctk.CTkLabel(
            help_card,
            text="📖  How to Use",
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary
        )
        help_title.pack(anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.md))
        
        instructions = """1. Click "Install All Scripts" to copy scripts to Resolve's script folder
2. Open DaVinci Resolve
3. Go to Workspace → Scripts → select any LTW script
4. Follow the on-screen prompts

Scripts are installed to:
~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/"""
        
        help_text = ctk.CTkLabel(
            help_card,
            text=instructions,
            font=get_font("sm"),
            text_color=theme.colors.text_secondary,
            justify="left"
        )
        help_text.pack(anchor="w", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        
    def _get_script_count(self) -> int:
        """Get number of available scripts"""
        if self.scripts_dir.exists():
            return len(list(self.scripts_dir.glob("*.lua")))
        return 0
        
    def _is_script_installed(self, name: str) -> bool:
        """Check if a script is installed in Resolve"""
        resolve_scripts_dir = Path.home() / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Comp"
        return (resolve_scripts_dir / f"{name}.lua").exists()
        
    def _install_script(self, name: str):
        """Install a single script"""
        source = self.scripts_dir / f"{name}.lua"
        if not source.exists():
            messagebox.showerror("Error", f"Script not found: {name}")
            return
            
        dest_dir = Path.home() / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Comp"
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            shutil.copy2(source, dest_dir / f"{name}.lua")
            messagebox.showinfo("Success", f"Installed {name} to Resolve!")
            
            if self.on_status_change:
                self.on_status_change(f"Installed {name}", "success")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to install: {e}")
            
    def _install_all_scripts(self):
        """Install all scripts to Resolve"""
        if not self.scripts_dir.exists():
            messagebox.showerror("Error", "Scripts directory not found")
            return
            
        dest_dir = Path.home() / "Library" / "Application Support" / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "Scripts" / "Comp"
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        installed = 0
        for script in self.scripts_dir.glob("*.lua"):
            try:
                shutil.copy2(script, dest_dir / script.name)
                installed += 1
            except Exception as e:
                print(f"Failed to install {script.name}: {e}")
                
        messagebox.showinfo("Complete", f"Installed {installed} scripts to DaVinci Resolve!")
        
        if self.on_status_change:
            self.on_status_change(f"Installed {installed} scripts", "success")
            
    def _open_scripts_folder(self):
        """Open scripts folder in Finder"""
        if self.scripts_dir.exists():
            os.system(f'open "{self.scripts_dir}"')
        else:
            messagebox.showerror("Error", "Scripts folder not found")
            
    def _open_luts_folder(self):
        """Open LUTs folder in Finder"""
        self.luts_dir.mkdir(parents=True, exist_ok=True)
        os.system(f'open "{self.luts_dir}"')
        
    def _copy_import_script(self):
        """Copy import script path to clipboard"""
        # Find the most recent import script
        resolve_dir = Path.home() / "Desktop" / "clips" / "resolve_project"
        if resolve_dir.exists():
            scripts = list(resolve_dir.glob("*_import.lua"))
            if scripts:
                latest = max(scripts, key=lambda p: p.stat().st_mtime)
                self.clipboard_clear()
                self.clipboard_append(str(latest))
                messagebox.showinfo("Copied", f"Import script path copied to clipboard:\n{latest}")
                return
                
        messagebox.showwarning("Not Found", "No import scripts found. Process some videos first!")
        
    def _add_custom_lut(self):
        """Add a custom LUT file"""
        filetypes = [("LUT files", "*.cube *.3dl *.lut")]
        file = filedialog.askopenfilename(title="Select LUT File", filetypes=filetypes)
        
        if file:
            self.luts_dir.mkdir(parents=True, exist_ok=True)
            dest = self.luts_dir / Path(file).name
            
            try:
                shutil.copy2(file, dest)
                messagebox.showinfo("Success", f"Added LUT: {Path(file).name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add LUT: {e}")

