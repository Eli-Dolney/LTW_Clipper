"""
LTW Video Editor Pro - Opus Clip AI Tab
AI-powered video processing for social media
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Callable, Optional, List, Dict, Any
from pathlib import Path
import threading
import sys
import os

from ..theme import theme, get_font
from ..components.file_picker import FilePicker
from ..components.progress_card import ProgressCard, StageStatus


class PlatformCard(ctk.CTkFrame):
    """Selectable platform card"""
    
    def __init__(self, parent, platform: str, icon: str, aspect: str,
                 selected: bool = False, on_toggle: Optional[Callable] = None, **kwargs):
        super().__init__(
            parent,
            fg_color=theme.colors.bg_tertiary if not selected else theme.colors.accent_primary,
            corner_radius=8,
            cursor="hand2",
            **kwargs
        )
        
        self.platform = platform
        self.selected = selected
        self.on_toggle = on_toggle
        
        self.bind("<Button-1>", self._on_click)
        
        # Content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(padx=theme.spacing.md, pady=theme.spacing.sm)
        content.bind("<Button-1>", self._on_click)
        
        icon_label = ctk.CTkLabel(
            content,
            text=icon,
            font=get_font("xl")
        )
        icon_label.pack()
        icon_label.bind("<Button-1>", self._on_click)
        
        name_label = ctk.CTkLabel(
            content,
            text=platform,
            font=get_font("sm", "bold"),
            text_color=theme.colors.text_primary
        )
        name_label.pack()
        name_label.bind("<Button-1>", self._on_click)
        
        aspect_label = ctk.CTkLabel(
            content,
            text=aspect,
            font=get_font("xs"),
            text_color=theme.colors.text_muted
        )
        aspect_label.pack()
        aspect_label.bind("<Button-1>", self._on_click)
        
    def _on_click(self, event):
        """Handle click"""
        self.selected = not self.selected
        self.configure(
            fg_color=theme.colors.accent_primary if self.selected else theme.colors.bg_tertiary
        )
        if self.on_toggle:
            self.on_toggle(self.platform, self.selected)
            
    def set_selected(self, selected: bool):
        """Set selection state"""
        self.selected = selected
        self.configure(
            fg_color=theme.colors.accent_primary if selected else theme.colors.bg_tertiary
        )


class OpusTab(ctk.CTkFrame):
    """Opus Clip AI processing tab"""
    
    def __init__(self, parent, on_status_change: Optional[Callable] = None,
                 on_stats_update: Optional[Callable] = None, **kwargs):
        super().__init__(
            parent,
            fg_color="transparent",
            **kwargs
        )
        
        self.on_status_change = on_status_change
        self.on_stats_update = on_stats_update
        self.is_processing = False
        self.selected_files: List[Path] = []
        self.selected_platforms: Dict[str, bool] = {
            "TikTok": True,
            "Instagram Reels": True,
            "YouTube Shorts": True,
            "Twitter": False,
            "LinkedIn": False
        }
        
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
            text="🤖  Opus Clip AI",
            font=get_font("2xl", "bold"),
            text_color=theme.colors.text_primary
        )
        title.pack(anchor="w")
        
        subtitle = ctk.CTkLabel(
            header,
            text="AI-powered video processing for social media optimization",
            font=get_font("md"),
            text_color=theme.colors.text_secondary
        )
        subtitle.pack(anchor="w", pady=(theme.spacing.xs, 0))
        
        # File Selection
        file_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius
        )
        file_card.pack(fill="x", pady=(0, theme.spacing.lg))
        
        file_title = ctk.CTkLabel(
            file_card,
            text="📁  Source Video",
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary
        )
        file_title.pack(anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.sm))
        
        self.file_picker = FilePicker(
            file_card,
            on_files_changed=self._on_files_changed,
            multiple=False
        )
        self.file_picker.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        
        # Platform Selection
        platform_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius
        )
        platform_card.pack(fill="x", pady=(0, theme.spacing.lg))
        
        platform_title = ctk.CTkLabel(
            platform_card,
            text="📱  Target Platforms",
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary
        )
        platform_title.pack(anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.sm))
        
        platform_desc = ctk.CTkLabel(
            platform_card,
            text="Select platforms to optimize clips for",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        platform_desc.pack(anchor="w", padx=theme.spacing.lg)
        
        # Platform grid
        platform_grid = ctk.CTkFrame(platform_card, fg_color="transparent")
        platform_grid.pack(fill="x", padx=theme.spacing.lg, pady=theme.spacing.lg)
        
        platforms = [
            ("TikTok", "📱", "9:16"),
            ("Instagram Reels", "📷", "9:16"),
            ("YouTube Shorts", "▶️", "9:16"),
            ("Twitter", "🐦", "1:1"),
            ("LinkedIn", "💼", "16:9")
        ]
        
        self.platform_cards: Dict[str, PlatformCard] = {}
        
        for platform, icon, aspect in platforms:
            card = PlatformCard(
                platform_grid,
                platform=platform,
                icon=icon,
                aspect=aspect,
                selected=self.selected_platforms.get(platform, False),
                on_toggle=self._on_platform_toggle
            )
            card.pack(side="left", padx=(0, theme.spacing.sm))
            self.platform_cards[platform] = card
            
        # AI Settings
        ai_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius
        )
        ai_card.pack(fill="x", pady=(0, theme.spacing.lg))
        
        ai_title = ctk.CTkLabel(
            ai_card,
            text="✨  AI Features",
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary
        )
        ai_title.pack(anchor="w", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.md))
        
        ai_content = ctk.CTkFrame(ai_card, fg_color="transparent")
        ai_content.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
        
        # AI Highlights
        self.ai_highlights_var = ctk.BooleanVar(value=True)
        ai_check = ctk.CTkCheckBox(
            ai_content,
            text="AI Highlight Detection",
            variable=self.ai_highlights_var,
            font=get_font("sm"),
            fg_color=theme.colors.accent_primary,
            hover_color=theme.colors.accent_hover
        )
        ai_check.pack(anchor="w", pady=(0, theme.spacing.sm))
        
        ai_desc = ctk.CTkLabel(
            ai_content,
            text="Automatically detect and extract the best moments",
            font=get_font("xs"),
            text_color=theme.colors.text_muted
        )
        ai_desc.pack(anchor="w", padx=(26, 0), pady=(0, theme.spacing.md))
        
        # Captions
        self.captions_var = ctk.BooleanVar(value=False)
        caption_check = ctk.CTkCheckBox(
            ai_content,
            text="Auto-Generate Captions",
            variable=self.captions_var,
            font=get_font("sm"),
            fg_color=theme.colors.accent_primary,
            hover_color=theme.colors.accent_hover
        )
        caption_check.pack(anchor="w", pady=(0, theme.spacing.sm))
        
        caption_desc = ctk.CTkLabel(
            ai_content,
            text="Add subtitles using speech-to-text (requires Whisper)",
            font=get_font("xs"),
            text_color=theme.colors.text_muted
        )
        caption_desc.pack(anchor="w", padx=(26, 0), pady=(0, theme.spacing.md))
        
        # Enhancement preset
        enhance_frame = ctk.CTkFrame(ai_content, fg_color="transparent")
        enhance_frame.pack(fill="x", pady=(0, theme.spacing.md))
        
        enhance_label = ctk.CTkLabel(
            enhance_frame,
            text="Enhancement Preset",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        enhance_label.pack(anchor="w")
        
        self.enhance_var = ctk.StringVar(value="social_media")
        enhance_menu = ctk.CTkOptionMenu(
            enhance_frame,
            values=["social_media", "vibrant", "cinematic", "clean", "gaming", "none"],
            variable=self.enhance_var,
            font=get_font("sm"),
            fg_color=theme.colors.bg_tertiary,
            button_color=theme.colors.bg_hover,
            button_hover_color=theme.colors.accent_primary,
            dropdown_fg_color=theme.colors.bg_secondary
        )
        enhance_menu.pack(anchor="w", pady=(theme.spacing.xs, 0))
        
        # Max clips slider
        clips_frame = ctk.CTkFrame(ai_content, fg_color="transparent")
        clips_frame.pack(fill="x")
        
        clips_label = ctk.CTkLabel(
            clips_frame,
            text="Maximum Clips to Generate",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        clips_label.pack(anchor="w")
        
        clips_control = ctk.CTkFrame(clips_frame, fg_color="transparent")
        clips_control.pack(fill="x", pady=(theme.spacing.xs, 0))
        
        self.clips_slider = ctk.CTkSlider(
            clips_control,
            from_=1,
            to=30,
            number_of_steps=29,
            fg_color=theme.colors.bg_tertiary,
            progress_color=theme.colors.accent_primary,
            button_color=theme.colors.accent_primary,
            command=self._on_clips_change
        )
        self.clips_slider.set(10)
        self.clips_slider.pack(side="left", fill="x", expand=True, padx=(0, theme.spacing.md))
        
        self.clips_value = ctk.CTkLabel(
            clips_control,
            text="10",
            font=get_font("md", "bold"),
            text_color=theme.colors.accent_primary,
            width=40
        )
        self.clips_value.pack(side="right")
        
        # Progress
        self.progress_card = ProgressCard(
            self.scroll_frame,
            title="AI Processing",
            stages=[
                "Content Analysis",
                "Highlight Detection",
                "Clip Generation",
                "Platform Optimization",
                "Final Export"
            ]
        )
        self.progress_card.pack(fill="x", pady=(0, theme.spacing.lg))
        
        # Action buttons
        action_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        action_frame.pack(fill="x")
        
        self.start_btn = ctk.CTkButton(
            action_frame,
            text="🚀  Start AI Processing",
            font=get_font("md", "bold"),
            height=48,
            command=self._start_processing,
            **theme.get_button_style("primary")
        )
        self.start_btn.pack(fill="x", pady=(0, theme.spacing.sm))
        
        self.stop_btn = ctk.CTkButton(
            action_frame,
            text="⏹️  Stop",
            font=get_font("sm"),
            height=36,
            state="disabled",
            command=self._stop_processing,
            **theme.get_button_style("danger")
        )
        self.stop_btn.pack(fill="x")
        
    def _on_files_changed(self, files: List[Path]):
        """Handle file selection"""
        self.selected_files = files
        
    def _on_platform_toggle(self, platform: str, selected: bool):
        """Handle platform toggle"""
        self.selected_platforms[platform] = selected
        
    def _on_clips_change(self, value):
        """Handle clips slider change"""
        self.clips_value.configure(text=str(int(value)))
        
    def _start_processing(self):
        """Start AI processing"""
        if not self.selected_files:
            messagebox.showwarning("No File", "Please select a video file first")
            return
            
        selected = [p for p, s in self.selected_platforms.items() if s]
        if not selected:
            messagebox.showwarning("No Platforms", "Please select at least one target platform")
            return
            
        self.is_processing = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_card.start_processing()
        
        if self.on_status_change:
            self.on_status_change("AI Processing...", "processing")
            
        thread = threading.Thread(target=self._process_video)
        thread.daemon = True
        thread.start()
        
    def _process_video(self):
        """Process video with AI"""
        try:
            # Simulate processing stages
            stages = [
                "Analyzing content...",
                "Detecting highlights...",
                "Generating clips...",
                "Optimizing for platforms...",
                "Exporting final clips..."
            ]
            
            for i, stage in enumerate(stages):
                if not self.is_processing:
                    break
                    
                progress = (i + 1) / len(stages)
                self.after(0, lambda p=progress, s=stage, idx=i: self._update_progress(p, s, idx))
                
                # Simulate work
                import time
                time.sleep(2)
                
            if self.is_processing:
                self.after(0, self._on_complete)
                
        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))
            
    def _update_progress(self, progress: float, status: str, stage_idx: int):
        """Update progress display"""
        self.progress_card.set_progress(progress, status)
        
        # Mark previous stages complete
        for i in range(stage_idx):
            self.progress_card.set_stage(i, StageStatus.COMPLETED)
        self.progress_card.set_stage(stage_idx, StageStatus.IN_PROGRESS)
        
    def _on_complete(self):
        """Handle processing complete"""
        self.is_processing = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_card.complete(success=True)
        
        if self.on_status_change:
            self.on_status_change("Ready", "success")
            
        platforms = [p for p, s in self.selected_platforms.items() if s]
        messagebox.showinfo("Complete", f"AI processing complete!\nOptimized for: {', '.join(platforms)}")
        
    def _on_error(self, error: str):
        """Handle error"""
        self.is_processing = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_card.complete(success=False)
        
        if self.on_status_change:
            self.on_status_change("Error", "error")
            
        messagebox.showerror("Error", f"Processing failed: {error}")
        
    def _stop_processing(self):
        """Stop processing"""
        self.is_processing = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_card.reset()
        
        if self.on_status_change:
            self.on_status_change("Stopped", "warning")
            
    def get_settings(self) -> Dict[str, Any]:
        """Get current settings"""
        return {
            'platforms': [p for p, s in self.selected_platforms.items() if s],
            'ai_highlights': self.ai_highlights_var.get(),
            'add_captions': self.captions_var.get(),
            'enhancement_preset': self.enhance_var.get(),
            'max_clips': int(self.clips_slider.get())
        }
        
    def apply_settings(self, settings: Dict[str, Any]):
        """Apply settings"""
        if 'platforms' in settings:
            for platform in self.selected_platforms:
                selected = platform.lower().replace(' ', '_') in [p.lower().replace(' ', '_') for p in settings['platforms']]
                self.selected_platforms[platform] = selected
                if platform in self.platform_cards:
                    self.platform_cards[platform].set_selected(selected)
        if 'ai_highlights' in settings:
            self.ai_highlights_var.set(settings['ai_highlights'])
        if 'add_captions' in settings:
            self.captions_var.set(settings['add_captions'])
        if 'enhancement_preset' in settings:
            self.enhance_var.set(settings['enhancement_preset'])
        if 'max_clips' in settings:
            self.clips_slider.set(settings['max_clips'])
            self.clips_value.configure(text=str(settings['max_clips']))

