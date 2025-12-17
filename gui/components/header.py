"""
LTW Video Editor Pro - Header Component
Top bar with logo, title, and quick actions
"""

import customtkinter as ctk
from typing import Callable, Optional
import sys
import os

# Import from parent package
from ..theme import theme, get_font


class Header(ctk.CTkFrame):
    """Professional header bar component"""
    
    def __init__(self, parent, on_settings: Optional[Callable] = None, **kwargs):
        super().__init__(
            parent,
            fg_color=theme.colors.bg_primary,
            height=theme.spacing.header_height,
            corner_radius=0,
            **kwargs
        )
        
        self.on_settings = on_settings
        self.pack_propagate(False)
        self._create_widgets()
        
    def _create_widgets(self):
        """Create header widgets"""
        # Left section - Logo and title
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.pack(side="left", fill="y", padx=theme.spacing.lg)
        
        # Logo icon (using emoji for now, could be replaced with image)
        logo_label = ctk.CTkLabel(
            left_frame,
            text="🎬",
            font=get_font("3xl"),
            text_color=theme.colors.accent_primary
        )
        logo_label.pack(side="left", padx=(0, theme.spacing.sm))
        
        # Title
        title_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        title_frame.pack(side="left", fill="y", pady=theme.spacing.sm)
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="LTW Video Editor Pro",
            font=get_font("xl", "bold"),
            text_color=theme.colors.text_primary
        )
        title_label.pack(anchor="w")
        
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="Professional Video Splitting & Editing Suite",
            font=get_font("xs"),
            text_color=theme.colors.text_muted
        )
        subtitle_label.pack(anchor="w")
        
        # Right section - Quick actions
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.pack(side="right", fill="y", padx=theme.spacing.lg)
        
        # Version badge
        version_badge = ctk.CTkLabel(
            right_frame,
            text="v2.0",
            font=get_font("xs"),
            text_color=theme.colors.text_muted,
            fg_color=theme.colors.bg_tertiary,
            corner_radius=4,
            padx=8,
            pady=2
        )
        version_badge.pack(side="left", padx=theme.spacing.sm, pady=theme.spacing.md)
        
        # Status indicator
        self.status_frame = ctk.CTkFrame(
            right_frame,
            fg_color=theme.colors.bg_tertiary,
            corner_radius=12,
            height=32,
            width=100
        )
        self.status_frame.pack(side="left", padx=theme.spacing.sm, pady=theme.spacing.md)
        
        self.status_dot = ctk.CTkLabel(
            self.status_frame,
            text="●",
            font=get_font("sm"),
            text_color=theme.colors.success,
            width=20
        )
        self.status_dot.pack(side="left", padx=(8, 0), pady=4)
        
        self.status_text = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        self.status_text.pack(side="left", padx=(4, 12), pady=4)
        
    def set_status(self, status: str, status_type: str = "success"):
        """Update status indicator"""
        color_map = {
            "success": theme.colors.success,
            "warning": theme.colors.warning,
            "error": theme.colors.error,
            "info": theme.colors.info,
            "processing": theme.colors.accent_primary
        }
        
        self.status_dot.configure(text_color=color_map.get(status_type, theme.colors.success))
        self.status_text.configure(text=status)

