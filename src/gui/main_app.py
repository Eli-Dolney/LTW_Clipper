"""
LTW Video Editor Pro - Main Application
Professional video editing suite with sidebar navigation
"""

import customtkinter as ctk
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .theme import theme, get_font
from .utils.preset_manager import Preset


class LTWVideoEditorPro:
    """Main application class"""
    
    def __init__(self):
        # Apply theme first
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("LTW Video Editor Pro")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Track current tab
        self.current_tab = "split"
        self.tabs: Dict[str, ctk.CTkFrame] = {}
        
        self._create_layout()
        self._center_window()
        
    def _create_layout(self):
        """Create the main layout"""
        # Main horizontal container
        c = theme.colors
        main_frame = ctk.CTkFrame(self.root, fg_color=c.bg_primary)
        main_frame.pack(fill="both", expand=True)
        
        # === HEADER ===
        header = ctk.CTkFrame(main_frame, fg_color=c.bg_secondary, height=60)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        # Logo and title
        logo = ctk.CTkLabel(header, text="🎬", font=ctk.CTkFont(size=32))
        logo.pack(side="left", padx=20)
        
        title = ctk.CTkLabel(
            header, 
            text="LTW Video Editor Pro", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white"
        )
        title.pack(side="left", padx=10)
        
        # Status
        self.status_label = ctk.CTkLabel(
            header,
            text="● Ready",
            font=ctk.CTkFont(size=12),
            text_color=c.success
        )
        self.status_label.pack(side="right", padx=20)
        
        # === BODY (Sidebar + Content) ===
        body = ctk.CTkFrame(main_frame, fg_color="transparent")
        body.pack(fill="both", expand=True, side="top")
        
        # === SIDEBAR ===
        sidebar = ctk.CTkFrame(body, fg_color=c.bg_secondary, width=220)
        sidebar.pack(fill="y", side="left")
        sidebar.pack_propagate(False)
        
        # Sidebar title
        nav_label = ctk.CTkLabel(
            sidebar,
            text="MAIN TOOLS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=c.text_muted
        )
        nav_label.pack(anchor="w", padx=16, pady=(20, 10))
        
        # Navigation buttons
        nav_items = [
            ("split", "✂️  Video Splitter"),
            ("templates", "🎛️  Templates"),
            ("text_studio", "✏️  Text Studio"),
            ("edit_suite", "🎞️  Edit Suite"),
            ("opus", "🤖  Opus Clip AI"),
            ("studio", "🎬  Studio"),
            ("resolve", "🎭  DaVinci Resolve"),
        ]
        
        self.nav_buttons = {}
        for tab_id, label in nav_items:
            btn = ctk.CTkButton(
                sidebar,
                text=label,
                font=ctk.CTkFont(size=14),
                height=44,
                anchor="w",
                fg_color=c.accent_primary if tab_id == "split" else "transparent",
                hover_color=c.accent_hover if tab_id == "split" else c.bg_hover,
                command=lambda t=tab_id: self._switch_tab(t)
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[tab_id] = btn
        
        # Settings section
        settings_label = ctk.CTkLabel(
            sidebar,
            text="CONFIGURATION",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=c.text_muted
        )
        settings_label.pack(anchor="w", padx=16, pady=(20, 10))
        
        settings_btn = ctk.CTkButton(
            sidebar,
            text="⚙️  Settings",
            font=ctk.CTkFont(size=14),
            height=44,
            anchor="w",
            fg_color="transparent",
            hover_color=c.bg_hover,
            command=lambda: self._switch_tab("settings")
        )
        settings_btn.pack(fill="x", padx=12, pady=2)
        self.nav_buttons["settings"] = settings_btn
        
        # === CONTENT AREA ===
        self.content_area = ctk.CTkFrame(body, fg_color=c.bg_dark)
        self.content_area.pack(fill="both", expand=True, side="right")
        
        # Create tabs
        self._create_tabs()
        
        # Show initial tab
        self._show_tab("split")
        
    def _create_tabs(self):
        """Create all tab contents"""
        # Import tabs here to avoid circular imports
        from .tabs.split_tab import SplitTab
        from .tabs.opus_tab import OpusTab
        from .tabs.resolve_tab import ResolveTab
        from .tabs.settings_tab import SettingsTab
        from .tabs.studio_tab import StudioTab
        from .tabs.templates_tab import TemplatesTab
        from .tabs.text_studio_tab import TextStudioTab
        from .tabs.edit_suite_tab import EditSuiteTab
        
        # Split Tab
        self.tabs["split"] = SplitTab(
            self.content_area,
            on_status_change=self._on_status_change,
            on_stats_update=lambda x: None
        )
        
        # Opus Clip Tab
        self.tabs["opus"] = OpusTab(
            self.content_area,
            on_status_change=self._on_status_change,
            on_stats_update=lambda x: None
        )

        # Templates Tab
        self.tabs["templates"] = TemplatesTab(
            self.content_area,
            on_status_change=self._on_status_change,
            on_apply_template=self._on_apply_template,
        )

        self.tabs["text_studio"] = TextStudioTab(
            self.content_area,
            on_status_change=self._on_status_change,
        )

        self.tabs["edit_suite"] = EditSuiteTab(
            self.content_area,
            on_status_change=self._on_status_change,
        )

        self.tabs["studio"] = StudioTab(
            self.content_area,
            on_status_change=self._on_status_change,
        )

        # Resolve Tab
        self.tabs["resolve"] = ResolveTab(
            self.content_area,
            on_status_change=self._on_status_change
        )
        
        # Settings Tab
        self.tabs["settings"] = SettingsTab(
            self.content_area,
            on_preset_apply=self._on_preset_apply,
            get_current_settings=self._get_current_settings,
            on_status_change=self._on_status_change
        )
        
    def _switch_tab(self, tab_id: str):
        """Switch to a different tab"""
        # Update button states
        for btn_id, btn in self.nav_buttons.items():
            if btn_id == tab_id:
                btn.configure(fg_color=theme.colors.accent_primary, hover_color=theme.colors.accent_hover)
            else:
                btn.configure(fg_color="transparent", hover_color=theme.colors.bg_hover)
        
        self._show_tab(tab_id)
        
    def _show_tab(self, tab_id: str):
        """Show a specific tab"""
        # Hide all tabs
        for tab in self.tabs.values():
            tab.pack_forget()
            
        # Show selected tab
        if tab_id in self.tabs:
            self.tabs[tab_id].pack(fill="both", expand=True)
            self.current_tab = tab_id
            
    def _on_status_change(self, status: str, status_type: str = "success"):
        """Handle status updates from tabs"""
        color_map = {
            "success": theme.colors.success,
            "warning": theme.colors.warning,
            "error": theme.colors.error,
            "info": theme.colors.info,
            "processing": theme.colors.accent_primary,
        }
        self.status_label.configure(
            text=f"● {status}",
            text_color=color_map.get(status_type, "#00d26a")
        )
        
    def _on_preset_apply(self, preset: Preset):
        """Apply a preset to the split tab"""
        settings = preset.to_dict()
        self.tabs["split"].apply_settings(settings)
        self.tabs["opus"].apply_settings(settings)
        self._switch_tab("split")
        
    def _on_apply_template(self, template):
        """Send a channel template into the Opus pipeline and switch to it."""
        self.tabs["opus"].set_active_template(template)
        self._switch_tab("opus")

    def _get_current_settings(self) -> Dict[str, Any]:
        """Get current settings from all tabs"""
        settings = {}
        if "split" in self.tabs:
            settings.update(self.tabs["split"].get_settings())
        if "opus" in self.tabs:
            settings.update(self.tabs["opus"].get_settings())
        return settings
        
    def _center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    print("🎬 Starting LTW Video Editor Pro...")
    app = LTWVideoEditorPro()
    app.run()


if __name__ == "__main__":
    main()
