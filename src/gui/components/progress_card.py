"""
LTW Video Editor Pro - Progress Card Component
Animated progress display with stages
"""

import customtkinter as ctk
from typing import List, Optional, Dict
from enum import Enum
import sys
import os

from ..theme import theme, get_font


def animate_progress(widget, target_value: float, duration: int = 300):
    """Animate progress bar to target value"""
    current = widget.get()
    steps = 20
    step_duration = duration // steps
    increment = (target_value - current) / steps
    
    def step(remaining_steps):
        if remaining_steps > 0:
            new_value = current + (steps - remaining_steps + 1) * increment
            widget.set(min(max(new_value, 0), 1))
            widget.after(step_duration, lambda: step(remaining_steps - 1))
    
    step(steps)


class StageStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


class StageIndicator(ctk.CTkFrame):
    """Single stage indicator with icon and label"""
    
    def __init__(self, parent, stage_num: int, label: str, **kwargs):
        super().__init__(
            parent,
            fg_color="transparent",
            **kwargs
        )
        
        self.stage_num = stage_num
        self.label = label
        self.status = StageStatus.PENDING
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Create stage indicator widgets"""
        # Icon/number circle
        self.icon_frame = ctk.CTkFrame(
            self,
            fg_color=theme.colors.bg_tertiary,
            width=32,
            height=32,
            corner_radius=16
        )
        self.icon_frame.pack(side="left")
        self.icon_frame.pack_propagate(False)
        
        self.icon_label = ctk.CTkLabel(
            self.icon_frame,
            text=str(self.stage_num),
            font=get_font("sm", "bold"),
            text_color=theme.colors.text_muted
        )
        self.icon_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Label
        self.text_label = ctk.CTkLabel(
            self,
            text=self.label,
            font=get_font("sm"),
            text_color=theme.colors.text_muted
        )
        self.text_label.pack(side="left", padx=(theme.spacing.sm, 0))
        
    def set_status(self, status: StageStatus):
        """Update stage status"""
        self.status = status
        
        if status == StageStatus.PENDING:
            self.icon_frame.configure(fg_color=theme.colors.bg_tertiary)
            self.icon_label.configure(text=str(self.stage_num), text_color=theme.colors.text_muted)
            self.text_label.configure(text_color=theme.colors.text_muted)
            
        elif status == StageStatus.IN_PROGRESS:
            self.icon_frame.configure(fg_color=theme.colors.accent_primary)
            self.icon_label.configure(text="●", text_color=theme.colors.text_primary)
            self.text_label.configure(text_color=theme.colors.text_primary)
            
        elif status == StageStatus.COMPLETED:
            self.icon_frame.configure(fg_color=theme.colors.success)
            self.icon_label.configure(text="✓", text_color=theme.colors.text_primary)
            self.text_label.configure(text_color=theme.colors.success)
            
        elif status == StageStatus.ERROR:
            self.icon_frame.configure(fg_color=theme.colors.error)
            self.icon_label.configure(text="✕", text_color=theme.colors.text_primary)
            self.text_label.configure(text_color=theme.colors.error)


class ProgressCard(ctk.CTkFrame):
    """Professional progress card with stages and progress bar"""
    
    def __init__(self, parent, title: str = "Processing", 
                 stages: Optional[List[str]] = None, **kwargs):
        super().__init__(
            parent,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius,
            **kwargs
        )
        
        self.title = title
        self.stages = stages or []
        self.stage_indicators: List[StageIndicator] = []
        self.current_stage = 0
        self.progress_value = 0.0
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Create progress card widgets"""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.md))
        
        self.title_label = ctk.CTkLabel(
            header_frame,
            text=self.title,
            font=get_font("lg", "bold"),
            text_color=theme.colors.text_primary
        )
        self.title_label.pack(side="left")
        
        self.percent_label = ctk.CTkLabel(
            header_frame,
            text="0%",
            font=get_font("lg", "bold"),
            text_color=theme.colors.accent_primary
        )
        self.percent_label.pack(side="right")
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self,
            fg_color=theme.colors.bg_tertiary,
            progress_color=theme.colors.accent_primary,
            height=8,
            corner_radius=4
        )
        self.progress_bar.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.md))
        self.progress_bar.set(0)
        
        # Status text
        self.status_label = ctk.CTkLabel(
            self,
            text="Ready to process",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        self.status_label.pack(anchor="w", padx=theme.spacing.lg, pady=(0, theme.spacing.md))
        
        # Stages (if provided)
        if self.stages:
            stages_frame = ctk.CTkFrame(self, fg_color="transparent")
            stages_frame.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))
            
            for i, stage_label in enumerate(self.stages):
                indicator = StageIndicator(stages_frame, i + 1, stage_label)
                indicator.pack(anchor="w", pady=2)
                self.stage_indicators.append(indicator)
                
    def set_progress(self, value: float, status_text: Optional[str] = None, animate: bool = True):
        """Update progress (0.0 to 1.0)"""
        self.progress_value = max(0.0, min(1.0, value))
        
        if animate and abs(self.progress_value - self.progress_bar.get()) > 0.01:
            animate_progress(self.progress_bar, self.progress_value)
        else:
            self.progress_bar.set(self.progress_value)
            
        self.percent_label.configure(text=f"{int(self.progress_value * 100)}%")
        
        if status_text:
            self.status_label.configure(text=status_text)
            
    def set_stage(self, stage_index: int, status: StageStatus):
        """Update a specific stage status"""
        if 0 <= stage_index < len(self.stage_indicators):
            self.stage_indicators[stage_index].set_status(status)
            
    def advance_stage(self):
        """Move to next stage"""
        if self.current_stage < len(self.stage_indicators):
            self.set_stage(self.current_stage, StageStatus.COMPLETED)
            self.current_stage += 1
            if self.current_stage < len(self.stage_indicators):
                self.set_stage(self.current_stage, StageStatus.IN_PROGRESS)
                
    def start_processing(self):
        """Initialize for processing"""
        self.current_stage = 0
        self.set_progress(0)
        if self.stage_indicators:
            self.set_stage(0, StageStatus.IN_PROGRESS)
            
    def complete(self, success: bool = True):
        """Mark processing as complete"""
        if success:
            self.set_progress(1.0, "Processing complete!")
            self.title_label.configure(text_color=theme.colors.success)
            for indicator in self.stage_indicators:
                indicator.set_status(StageStatus.COMPLETED)
        else:
            self.title_label.configure(text_color=theme.colors.error)
            if self.stage_indicators and self.current_stage < len(self.stage_indicators):
                self.set_stage(self.current_stage, StageStatus.ERROR)
                
    def reset(self):
        """Reset to initial state"""
        self.current_stage = 0
        self.set_progress(0, "Ready to process")
        self.title_label.configure(text_color=theme.colors.text_primary)
        for indicator in self.stage_indicators:
            indicator.set_status(StageStatus.PENDING)

