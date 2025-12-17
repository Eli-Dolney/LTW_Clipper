"""
LTW Video Editor Pro - Sidebar Navigation Component
"""

import customtkinter as ctk
from typing import Callable, List, Dict, Optional
import sys
import os

from ..theme import theme, get_font


class NavButton(ctk.CTkButton):
    """Custom navigation button with icon and label"""
    
    def __init__(self, parent, icon: str, text: str, active: bool = False, 
                 command: Optional[Callable] = None, **kwargs):
        
        style = theme.get_sidebar_button_style(active)
        
        super().__init__(
            parent,
            text=f"  {icon}  {text}",
            font=get_font("md"),
            height=44,
            anchor="w",
            command=command,
            **style,
            **kwargs
        )
        
        self.icon = icon
        self.label_text = text
        self._active = active
        
    def set_active(self, active: bool):
        """Set button active state"""
        self._active = active
        style = theme.get_sidebar_button_style(active)
        self.configure(**style)


class Sidebar(ctk.CTkFrame):
    """Professional sidebar navigation component"""
    
    def __init__(self, parent, on_tab_change: Optional[Callable] = None, **kwargs):
        super().__init__(
            parent,
            fg_color=theme.colors.bg_secondary,
            width=theme.spacing.sidebar_width,
            corner_radius=0,
            **kwargs
        )
        
        self.on_tab_change = on_tab_change
        self.nav_buttons: Dict[str, NavButton] = {}
        self.current_tab = "split"
        
        self.pack_propagate(False)
        self._create_widgets()
        
    def _create_widgets(self):
        """Create sidebar widgets"""
        # Navigation section
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=theme.spacing.md, pady=theme.spacing.lg)
        
        # Section label
        section_label = ctk.CTkLabel(
            nav_frame,
            text="MAIN TOOLS",
            font=get_font("xs", "bold"),
            text_color=theme.colors.text_muted
        )
        section_label.pack(anchor="w", pady=(0, theme.spacing.sm))
        
        # Navigation items
        nav_items = [
            ("split", "✂️", "Video Splitter"),
            ("opus", "🤖", "Opus Clip AI"),
            ("resolve", "🎭", "DaVinci Resolve"),
        ]
        
        for tab_id, icon, label in nav_items:
            btn = NavButton(
                nav_frame,
                icon=icon,
                text=label,
                active=(tab_id == self.current_tab),
                command=lambda t=tab_id: self._on_nav_click(t)
            )
            btn.pack(fill="x", pady=2)
            self.nav_buttons[tab_id] = btn
        
        # Separator
        separator = ctk.CTkFrame(
            self,
            fg_color=theme.colors.border_default,
            height=1
        )
        separator.pack(fill="x", padx=theme.spacing.lg, pady=theme.spacing.lg)
        
        # Settings section
        settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        settings_frame.pack(fill="x", padx=theme.spacing.md)
        
        settings_label = ctk.CTkLabel(
            settings_frame,
            text="CONFIGURATION",
            font=get_font("xs", "bold"),
            text_color=theme.colors.text_muted
        )
        settings_label.pack(anchor="w", pady=(0, theme.spacing.sm))
        
        settings_btn = NavButton(
            settings_frame,
            icon="⚙️",
            text="Settings",
            active=False,
            command=lambda: self._on_nav_click("settings")
        )
        settings_btn.pack(fill="x", pady=2)
        self.nav_buttons["settings"] = settings_btn
        
        # Spacer
        spacer = ctk.CTkFrame(self, fg_color="transparent")
        spacer.pack(fill="both", expand=True)
        
        # Bottom section - Quick stats
        stats_frame = ctk.CTkFrame(
            self,
            fg_color=theme.colors.bg_tertiary,
            corner_radius=theme.spacing.card_radius
        )
        stats_frame.pack(fill="x", padx=theme.spacing.md, pady=theme.spacing.lg)
        
        stats_title = ctk.CTkLabel(
            stats_frame,
            text="Quick Stats",
            font=get_font("sm", "bold"),
            text_color=theme.colors.text_primary
        )
        stats_title.pack(anchor="w", padx=theme.spacing.md, pady=(theme.spacing.md, theme.spacing.xs))
        
        self.stats_content = ctk.CTkLabel(
            stats_frame,
            text="No videos processed yet",
            font=get_font("xs"),
            text_color=theme.colors.text_muted,
            wraplength=180,
            justify="left"
        )
        self.stats_content.pack(anchor="w", padx=theme.spacing.md, pady=(0, theme.spacing.md))
        
    def _on_nav_click(self, tab_id: str):
        """Handle navigation button click"""
        if tab_id == self.current_tab:
            return
            
        # Update button states
        for btn_id, btn in self.nav_buttons.items():
            btn.set_active(btn_id == tab_id)
        
        self.current_tab = tab_id
        
        if self.on_tab_change:
            self.on_tab_change(tab_id)
            
    def update_stats(self, stats_text: str):
        """Update quick stats display"""
        self.stats_content.configure(text=stats_text)
        
    def set_active_tab(self, tab_id: str):
        """Programmatically set active tab"""
        self._on_nav_click(tab_id)

