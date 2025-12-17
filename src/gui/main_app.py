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
        main_frame = ctk.CTkFrame(self.root, fg_color="#13131f")
        main_frame.pack(fill="both", expand=True)
        
        # === HEADER ===
        header = ctk.CTkFrame(main_frame, fg_color="#1a1a2e", height=60)
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
            text_color="#00d26a"
        )
        self.status_label.pack(side="right", padx=20)
        
        # === BODY (Sidebar + Content) ===
        body = ctk.CTkFrame(main_frame, fg_color="transparent")
        body.pack(fill="both", expand=True, side="top")
        
        # === SIDEBAR ===
        sidebar = ctk.CTkFrame(body, fg_color="#1a1a2e", width=220)
        sidebar.pack(fill="y", side="left")
        sidebar.pack_propagate(False)
        
        # Sidebar title
        nav_label = ctk.CTkLabel(
            sidebar,
            text="MAIN TOOLS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#6b6b80"
        )
        nav_label.pack(anchor="w", padx=16, pady=(20, 10))
        
        # Navigation buttons
        nav_items = [
            ("split", "✂️  Video Splitter"),
            ("opus", "🤖  Opus Clip AI"),
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
                fg_color="#0066ff" if tab_id == "split" else "transparent",
                hover_color="#0052cc" if tab_id == "split" else "#2d2d44",
                command=lambda t=tab_id: self._switch_tab(t)
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[tab_id] = btn
        
        # Settings section
        settings_label = ctk.CTkLabel(
            sidebar,
            text="CONFIGURATION",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#6b6b80"
        )
        settings_label.pack(anchor="w", padx=16, pady=(20, 10))
        
        settings_btn = ctk.CTkButton(
            sidebar,
            text="⚙️  Settings",
            font=ctk.CTkFont(size=14),
            height=44,
            anchor="w",
            fg_color="transparent",
            hover_color="#2d2d44",
            command=lambda: self._switch_tab("settings")
        )
        settings_btn.pack(fill="x", padx=12, pady=2)
        self.nav_buttons["settings"] = settings_btn
        
        # === CONTENT AREA ===
        self.content_area = ctk.CTkFrame(body, fg_color="#0d0d14")
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
                btn.configure(fg_color="#0066ff", hover_color="#0052cc")
            else:
                btn.configure(fg_color="transparent", hover_color="#2d2d44")
        
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
            "success": "#00d26a",
            "warning": "#ffb800",
            "error": "#ff4757",
            "info": "#00b4d8",
            "processing": "#0066ff"
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
