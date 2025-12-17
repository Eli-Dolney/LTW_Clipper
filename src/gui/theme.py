"""
LTW Video Editor Pro - Custom Theme System
Professional dark theme with distinctive accent colors
"""

import customtkinter as ctk
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class ColorPalette:
    """Color palette for the application"""
    # Primary backgrounds
    bg_dark: str = "#0d0d14"           # Deepest background
    bg_primary: str = "#13131f"         # Main background
    bg_secondary: str = "#1a1a2e"       # Card backgrounds
    bg_tertiary: str = "#242438"        # Elevated surfaces
    bg_hover: str = "#2d2d44"           # Hover states
    
    # Accent colors - Electric blue theme
    accent_primary: str = "#0066ff"     # Primary accent
    accent_secondary: str = "#3d8bff"   # Secondary accent
    accent_hover: str = "#0052cc"       # Accent hover
    accent_glow: str = "#0066ff33"      # Glow effect (with alpha)
    
    # Status colors
    success: str = "#00d26a"            # Success green
    warning: str = "#ffb800"            # Warning amber
    error: str = "#ff4757"              # Error red
    info: str = "#00b4d8"               # Info cyan
    
    # Text colors
    text_primary: str = "#ffffff"       # Primary text
    text_secondary: str = "#a0a0b8"     # Secondary text
    text_muted: str = "#6b6b80"         # Muted text
    text_disabled: str = "#4a4a5c"      # Disabled text
    
    # Border colors
    border_default: str = "#2a2a3c"     # Default borders
    border_hover: str = "#3a3a50"       # Hover borders
    border_focus: str = "#0066ff"       # Focus borders
    
    # Gradients (CSS-style)
    gradient_primary: str = "linear-gradient(135deg, #0066ff 0%, #00d4ff 100%)"
    gradient_dark: str = "linear-gradient(180deg, #1a1a2e 0%, #0d0d14 100%)"


@dataclass 
class Typography:
    """Typography settings"""
    font_family: str = "SF Pro Display"
    font_family_mono: str = "JetBrains Mono"
    
    # Font sizes
    size_xs: int = 10
    size_sm: int = 12
    size_md: int = 14
    size_lg: int = 16
    size_xl: int = 20
    size_2xl: int = 24
    size_3xl: int = 32
    size_4xl: int = 40


@dataclass
class Spacing:
    """Spacing and sizing constants"""
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32
    
    # Component sizes
    sidebar_width: int = 220
    header_height: int = 60
    card_radius: int = 12
    button_radius: int = 8
    input_radius: int = 8


class Theme:
    """Main theme class with all styling"""
    
    def __init__(self):
        self.colors = ColorPalette()
        self.typography = Typography()
        self.spacing = Spacing()
        
    def apply_to_customtkinter(self):
        """Apply theme to CustomTkinter globally"""
        ctk.set_appearance_mode("dark")
        
        # Note: CustomTkinter doesn't support full custom themes
        # We'll apply colors directly to widgets
        
    def get_button_style(self, variant: str = "primary") -> Dict:
        """Get button styling based on variant"""
        styles = {
            "primary": {
                "fg_color": self.colors.accent_primary,
                "hover_color": self.colors.accent_hover,
                "text_color": self.colors.text_primary,
                "corner_radius": self.spacing.button_radius,
            },
            "secondary": {
                "fg_color": self.colors.bg_tertiary,
                "hover_color": self.colors.bg_hover,
                "text_color": self.colors.text_primary,
                "corner_radius": self.spacing.button_radius,
            },
            "ghost": {
                "fg_color": "transparent",
                "hover_color": self.colors.bg_tertiary,
                "text_color": self.colors.text_secondary,
                "corner_radius": self.spacing.button_radius,
            },
            "danger": {
                "fg_color": self.colors.error,
                "hover_color": "#cc3a47",
                "text_color": self.colors.text_primary,
                "corner_radius": self.spacing.button_radius,
            },
            "success": {
                "fg_color": self.colors.success,
                "hover_color": "#00b85e",
                "text_color": self.colors.text_primary,
                "corner_radius": self.spacing.button_radius,
            }
        }
        return styles.get(variant, styles["primary"])
    
    def get_input_style(self) -> Dict:
        """Get input field styling"""
        return {
            "fg_color": self.colors.bg_tertiary,
            "border_color": self.colors.border_default,
            "text_color": self.colors.text_primary,
            "placeholder_text_color": self.colors.text_muted,
            "corner_radius": self.spacing.input_radius,
        }
    
    def get_card_style(self) -> Dict:
        """Get card container styling"""
        return {
            "fg_color": self.colors.bg_secondary,
            "corner_radius": self.spacing.card_radius,
        }
    
    def get_sidebar_button_style(self, active: bool = False) -> Dict:
        """Get sidebar navigation button styling"""
        if active:
            return {
                "fg_color": self.colors.accent_primary,
                "hover_color": self.colors.accent_hover,
                "text_color": self.colors.text_primary,
                "corner_radius": self.spacing.button_radius,
            }
        return {
            "fg_color": "transparent",
            "hover_color": self.colors.bg_tertiary,
            "text_color": self.colors.text_secondary,
            "corner_radius": self.spacing.button_radius,
        }


# Global theme instance
theme = Theme()


def get_font(size: str = "md", weight: str = "normal", mono: bool = False) -> ctk.CTkFont:
    """Get a font with specified properties"""
    t = theme.typography
    
    size_map = {
        "xs": t.size_xs,
        "sm": t.size_sm,
        "md": t.size_md,
        "lg": t.size_lg,
        "xl": t.size_xl,
        "2xl": t.size_2xl,
        "3xl": t.size_3xl,
        "4xl": t.size_4xl,
    }
    
    font_size = size_map.get(size, t.size_md)
    font_family = t.font_family_mono if mono else t.font_family
    font_weight = "bold" if weight == "bold" else "normal"
    
    return ctk.CTkFont(family=font_family, size=font_size, weight=font_weight)


def apply_hover_effect(widget, normal_color: str, hover_color: str):
    """Apply hover effect to a widget"""
    def on_enter(e):
        widget.configure(fg_color=hover_color)
    
    def on_leave(e):
        widget.configure(fg_color=normal_color)
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)

