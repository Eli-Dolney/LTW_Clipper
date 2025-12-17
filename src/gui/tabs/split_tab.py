"""
LTW Video Editor Pro - Video Splitter Tab
Main video splitting interface with all customization options
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


class SettingCard(ctk.CTkFrame):
    """Card for a group of settings"""
    
    def __init__(self, parent, title: str, icon: str = "", **kwargs):
        super().__init__(
            parent,
            fg_color=theme.colors.bg_secondary,
            corner_radius=theme.spacing.card_radius,
            **kwargs
        )
        
        # Title bar
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=theme.spacing.lg, pady=(theme.spacing.lg, theme.spacing.md))
        
        title_label = ctk.CTkLabel(
            title_frame,
            text=f"{icon}  {title}" if icon else title,
            font=get_font("md", "bold"),
            text_color=theme.colors.text_primary
        )
        title_label.pack(anchor="w")
        
        # Content frame
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="x", padx=theme.spacing.lg, pady=(0, theme.spacing.lg))


class SplitTab(ctk.CTkFrame):
    """Video Splitter tab with all customization options"""
    
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
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Create tab widgets"""
        # Scrollable container
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=theme.spacing.lg, pady=theme.spacing.lg)
        
        # Tab header
        header = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, theme.spacing.xl))
        
        title = ctk.CTkLabel(
            header,
            text="✂️  Video Splitter",
            font=get_font("2xl", "bold"),
            text_color=theme.colors.text_primary
        )
        title.pack(anchor="w")
        
        subtitle = ctk.CTkLabel(
            header,
            text="Split videos into clips with custom duration, quality, and naming",
            font=get_font("md"),
            text_color=theme.colors.text_secondary
        )
        subtitle.pack(anchor="w", pady=(theme.spacing.xs, 0))
        
        # Two-column layout
        columns = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        columns.pack(fill="both", expand=True)
        
        # Left column
        left_col = ctk.CTkFrame(columns, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, theme.spacing.md))
        
        # Right column
        right_col = ctk.CTkFrame(columns, fg_color="transparent")
        right_col.pack(side="right", fill="both", expand=True, padx=(theme.spacing.md, 0))
        
        # === LEFT COLUMN ===
        
        # File Selection Card
        file_card = SettingCard(left_col, "Video Files", "📁")
        file_card.pack(fill="x", pady=(0, theme.spacing.md))
        
        self.file_picker = FilePicker(
            file_card.content,
            on_files_changed=self._on_files_changed
        )
        self.file_picker.pack(fill="x")
        
        # Clip Settings Card
        clip_card = SettingCard(left_col, "Clip Settings", "⚙️")
        clip_card.pack(fill="x", pady=(0, theme.spacing.md))
        
        # Duration
        duration_frame = ctk.CTkFrame(clip_card.content, fg_color="transparent")
        duration_frame.pack(fill="x", pady=(0, theme.spacing.md))
        
        duration_label = ctk.CTkLabel(
            duration_frame,
            text="Clip Duration",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        duration_label.pack(anchor="w")
        
        duration_control = ctk.CTkFrame(duration_frame, fg_color="transparent")
        duration_control.pack(fill="x", pady=(theme.spacing.xs, 0))
        
        self.duration_slider = ctk.CTkSlider(
            duration_control,
            from_=5,
            to=120,
            number_of_steps=23,
            fg_color=theme.colors.bg_tertiary,
            progress_color=theme.colors.accent_primary,
            button_color=theme.colors.accent_primary,
            button_hover_color=theme.colors.accent_hover,
            command=self._on_duration_change
        )
        self.duration_slider.set(30)
        self.duration_slider.pack(side="left", fill="x", expand=True, padx=(0, theme.spacing.md))
        
        self.duration_value = ctk.CTkLabel(
            duration_control,
            text="30s",
            font=get_font("md", "bold"),
            text_color=theme.colors.accent_primary,
            width=50
        )
        self.duration_value.pack(side="right")
        
        # Quality
        quality_frame = ctk.CTkFrame(clip_card.content, fg_color="transparent")
        quality_frame.pack(fill="x", pady=(0, theme.spacing.md))
        
        quality_label = ctk.CTkLabel(
            quality_frame,
            text="Video Quality",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        quality_label.pack(anchor="w")
        
        self.quality_var = ctk.StringVar(value="youtube_hd")
        
        quality_options = ctk.CTkFrame(quality_frame, fg_color="transparent")
        quality_options.pack(fill="x", pady=(theme.spacing.xs, 0))
        
        qualities = [
            ("SD", "youtube_sd", "480p"),
            ("HD", "youtube_hd", "1080p"),
            ("4K", "youtube_4k", "2160p"),
            ("Original", "original", "Source")
        ]
        
        for label, value, desc in qualities:
            btn_frame = ctk.CTkFrame(quality_options, fg_color="transparent")
            btn_frame.pack(side="left", padx=(0, theme.spacing.sm))
            
            btn = ctk.CTkRadioButton(
                btn_frame,
                text=label,
                variable=self.quality_var,
                value=value,
                font=get_font("sm"),
                fg_color=theme.colors.accent_primary,
                hover_color=theme.colors.accent_hover
            )
            btn.pack()
            
            desc_label = ctk.CTkLabel(
                btn_frame,
                text=desc,
                font=get_font("xs"),
                text_color=theme.colors.text_muted
            )
            desc_label.pack()
        
        # Scene Detection
        detection_frame = ctk.CTkFrame(clip_card.content, fg_color="transparent")
        detection_frame.pack(fill="x", pady=(0, theme.spacing.sm))
        
        self.scene_detect_var = ctk.BooleanVar(value=False)
        scene_check = ctk.CTkCheckBox(
            detection_frame,
            text="Enable Scene Detection",
            variable=self.scene_detect_var,
            font=get_font("sm"),
            fg_color=theme.colors.accent_primary,
            hover_color=theme.colors.accent_hover,
            command=self._on_scene_detect_toggle
        )
        scene_check.pack(anchor="w")
        
        scene_desc = ctk.CTkLabel(
            detection_frame,
            text="AI-powered splitting at natural scene boundaries",
            font=get_font("xs"),
            text_color=theme.colors.text_muted
        )
        scene_desc.pack(anchor="w", padx=(26, 0))
        
        # Scene sensitivity (hidden by default)
        self.sensitivity_frame = ctk.CTkFrame(clip_card.content, fg_color="transparent")
        
        sens_label = ctk.CTkLabel(
            self.sensitivity_frame,
            text="Detection Sensitivity",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        sens_label.pack(anchor="w")
        
        sens_control = ctk.CTkFrame(self.sensitivity_frame, fg_color="transparent")
        sens_control.pack(fill="x", pady=(theme.spacing.xs, 0))
        
        self.sensitivity_slider = ctk.CTkSlider(
            sens_control,
            from_=0.1,
            to=0.9,
            fg_color=theme.colors.bg_tertiary,
            progress_color=theme.colors.accent_primary,
            button_color=theme.colors.accent_primary,
            button_hover_color=theme.colors.accent_hover
        )
        self.sensitivity_slider.set(0.3)
        self.sensitivity_slider.pack(side="left", fill="x", expand=True)
        
        # === RIGHT COLUMN ===
        
        # Output Settings Card
        output_card = SettingCard(right_col, "Output Settings", "📂")
        output_card.pack(fill="x", pady=(0, theme.spacing.md))
        
        # Output directory
        output_frame = ctk.CTkFrame(output_card.content, fg_color="transparent")
        output_frame.pack(fill="x", pady=(0, theme.spacing.md))
        
        output_label = ctk.CTkLabel(
            output_frame,
            text="Output Directory",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        output_label.pack(anchor="w")
        
        output_control = ctk.CTkFrame(output_frame, fg_color="transparent")
        output_control.pack(fill="x", pady=(theme.spacing.xs, 0))
        
        self.output_var = ctk.StringVar(value=str(Path.home() / "Desktop" / "clips"))
        self.output_entry = ctk.CTkEntry(
            output_control,
            textvariable=self.output_var,
            font=get_font("sm"),
            **theme.get_input_style()
        )
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, theme.spacing.sm))
        
        output_btn = ctk.CTkButton(
            output_control,
            text="Browse",
            font=get_font("sm"),
            width=80,
            command=self._browse_output,
            **theme.get_button_style("secondary")
        )
        output_btn.pack(side="right")
        
        # Project name
        project_frame = ctk.CTkFrame(output_card.content, fg_color="transparent")
        project_frame.pack(fill="x", pady=(0, theme.spacing.md))
        
        project_label = ctk.CTkLabel(
            project_frame,
            text="Project Name (optional)",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        project_label.pack(anchor="w")
        
        self.project_var = ctk.StringVar(value="")
        project_entry = ctk.CTkEntry(
            project_frame,
            textvariable=self.project_var,
            font=get_font("sm"),
            placeholder_text="Auto-generated if empty",
            **theme.get_input_style()
        )
        project_entry.pack(fill="x", pady=(theme.spacing.xs, 0))
        
        # Naming pattern
        naming_frame = ctk.CTkFrame(output_card.content, fg_color="transparent")
        naming_frame.pack(fill="x")
        
        naming_label = ctk.CTkLabel(
            naming_frame,
            text="Naming Pattern",
            font=get_font("sm"),
            text_color=theme.colors.text_secondary
        )
        naming_label.pack(anchor="w")
        
        self.naming_var = ctk.StringVar(value="{name}_part_{num:03d}")
        naming_entry = ctk.CTkEntry(
            naming_frame,
            textvariable=self.naming_var,
            font=get_font("sm", mono=True),
            **theme.get_input_style()
        )
        naming_entry.pack(fill="x", pady=(theme.spacing.xs, 0))
        
        naming_help = ctk.CTkLabel(
            naming_frame,
            text="Use {name}, {num}, {duration}, {timestamp}",
            font=get_font("xs"),
            text_color=theme.colors.text_muted
        )
        naming_help.pack(anchor="w", pady=(2, 0))
        
        # Integration Card
        integrate_card = SettingCard(right_col, "Integration", "🔗")
        integrate_card.pack(fill="x", pady=(0, theme.spacing.md))
        
        self.resolve_var = ctk.BooleanVar(value=True)
        resolve_check = ctk.CTkCheckBox(
            integrate_card.content,
            text="Generate DaVinci Resolve Project",
            variable=self.resolve_var,
            font=get_font("sm"),
            fg_color=theme.colors.accent_primary,
            hover_color=theme.colors.accent_hover
        )
        resolve_check.pack(anchor="w")
        
        resolve_desc = ctk.CTkLabel(
            integrate_card.content,
            text="Create Lua import script for easy Resolve integration",
            font=get_font("xs"),
            text_color=theme.colors.text_muted
        )
        resolve_desc.pack(anchor="w", padx=(26, 0))
        
        # Progress Card
        self.progress_card = ProgressCard(
            right_col,
            title="Processing",
            stages=["Analyzing video", "Creating clips", "Generating metadata", "Finalizing"]
        )
        self.progress_card.pack(fill="x", pady=(0, theme.spacing.md))
        
        # Action buttons
        action_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        action_frame.pack(fill="x")
        
        self.start_btn = ctk.CTkButton(
            action_frame,
            text="🚀  Start Processing",
            font=get_font("md", "bold"),
            height=48,
            command=self._start_processing,
            **theme.get_button_style("primary")
        )
        self.start_btn.pack(fill="x", pady=(0, theme.spacing.sm))
        
        btn_row = ctk.CTkFrame(action_frame, fg_color="transparent")
        btn_row.pack(fill="x")
        
        self.preview_btn = ctk.CTkButton(
            btn_row,
            text="👁️  Preview",
            font=get_font("sm"),
            height=36,
            command=self._preview_clips,
            **theme.get_button_style("secondary")
        )
        self.preview_btn.pack(side="left", fill="x", expand=True, padx=(0, theme.spacing.xs))
        
        self.stop_btn = ctk.CTkButton(
            btn_row,
            text="⏹️  Stop",
            font=get_font("sm"),
            height=36,
            state="disabled",
            command=self._stop_processing,
            **theme.get_button_style("danger")
        )
        self.stop_btn.pack(side="right", fill="x", expand=True, padx=(theme.spacing.xs, 0))
        
    def _on_files_changed(self, files: List[Path]):
        """Handle file selection change"""
        self.selected_files = files
        self._update_preview_estimate()
        
    def _on_duration_change(self, value):
        """Handle duration slider change"""
        duration = int(value)
        self.duration_value.configure(text=f"{duration}s")
        self._update_preview_estimate()
        
    def _on_scene_detect_toggle(self):
        """Handle scene detection toggle"""
        if self.scene_detect_var.get():
            self.sensitivity_frame.pack(fill="x", pady=(theme.spacing.sm, 0))
        else:
            self.sensitivity_frame.pack_forget()
            
    def _browse_output(self):
        """Open output directory browser"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_var.set(directory)
            
    def _update_preview_estimate(self):
        """Update estimated clip count"""
        if not self.selected_files:
            return
            
        # Calculate estimate (simplified)
        duration = int(self.duration_slider.get())
        total_clips = 0
        
        for file in self.selected_files:
            # Rough estimate: assume 60s per MB for a rough duration estimate
            try:
                file_size_mb = file.stat().st_size / (1024 * 1024)
                estimated_duration = file_size_mb * 60 / 10  # Very rough estimate
                clips = max(1, int(estimated_duration / duration))
                total_clips += clips
            except:
                total_clips += 1
                
        if self.on_stats_update:
            self.on_stats_update(f"~{total_clips} clips from {len(self.selected_files)} video(s)")
            
    def _preview_clips(self):
        """Show preview of clips to be created"""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select video files first")
            return
            
        duration = int(self.duration_slider.get())
        quality = self.quality_var.get()
        
        preview_text = f"Settings:\n"
        preview_text += f"• Duration: {duration} seconds\n"
        preview_text += f"• Quality: {quality}\n"
        preview_text += f"• Scene Detection: {'Yes' if self.scene_detect_var.get() else 'No'}\n"
        preview_text += f"• Output: {self.output_var.get()}\n\n"
        preview_text += f"Files to process:\n"
        
        for file in self.selected_files:
            preview_text += f"• {file.name}\n"
            
        messagebox.showinfo("Preview", preview_text)
        
    def _start_processing(self):
        """Start video processing"""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select video files first")
            return
            
        if self.is_processing:
            return
            
        self.is_processing = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_card.start_processing()
        
        if self.on_status_change:
            self.on_status_change("Processing...", "processing")
            
        # Start processing in background
        thread = threading.Thread(target=self._process_videos)
        thread.daemon = True
        thread.start()
        
    def _process_videos(self):
        """Process videos in background thread"""
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
            from src.core.video_splitter import VideoSplitter
            
            splitter = VideoSplitter(
                output_dir=self.output_var.get(),
                clip_duration=int(self.duration_slider.get()),
                quality=self.quality_var.get(),
                resolve_integration=self.resolve_var.get(),
                project_name=self.project_var.get() or None,
                scene_detection=self.scene_detect_var.get(),
                naming_pattern=self.naming_var.get()
            )
            
            total_clips = 0
            total_files = len(self.selected_files)
            
            for i, video_file in enumerate(self.selected_files):
                if not self.is_processing:
                    break
                    
                # Update progress
                progress = (i / total_files) * 0.9
                self.after(0, lambda p=progress, f=video_file.name: self._update_ui_progress(p, f"Processing {f}"))
                
                try:
                    clips = splitter.split_video(video_file)
                    total_clips += clips
                except Exception as e:
                    print(f"Error processing {video_file.name}: {e}")
                    
            # Complete
            self.after(0, lambda: self._on_complete(total_clips))
            
        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))
            
    def _update_ui_progress(self, progress: float, status: str):
        """Update UI progress (called from main thread)"""
        self.progress_card.set_progress(progress, status)
        
        # Update stage based on progress
        if progress < 0.25:
            self.progress_card.set_stage(0, StageStatus.IN_PROGRESS)
        elif progress < 0.5:
            self.progress_card.set_stage(0, StageStatus.COMPLETED)
            self.progress_card.set_stage(1, StageStatus.IN_PROGRESS)
        elif progress < 0.75:
            self.progress_card.set_stage(1, StageStatus.COMPLETED)
            self.progress_card.set_stage(2, StageStatus.IN_PROGRESS)
        else:
            self.progress_card.set_stage(2, StageStatus.COMPLETED)
            self.progress_card.set_stage(3, StageStatus.IN_PROGRESS)
            
    def _on_complete(self, total_clips: int):
        """Handle processing complete"""
        self.is_processing = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_card.complete(success=True)
        
        if self.on_status_change:
            self.on_status_change("Ready", "success")
            
        if self.on_stats_update:
            self.on_stats_update(f"Created {total_clips} clips")
            
        messagebox.showinfo("Complete", f"Successfully created {total_clips} video clips!")
        
    def _on_error(self, error: str):
        """Handle processing error"""
        self.is_processing = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_card.complete(success=False)
        
        if self.on_status_change:
            self.on_status_change("Error", "error")
            
        messagebox.showerror("Error", f"Processing failed: {error}")
        
    def _stop_processing(self):
        """Stop video processing"""
        self.is_processing = False
        self.progress_card.set_progress(0, "Stopped")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        
        if self.on_status_change:
            self.on_status_change("Stopped", "warning")
            
    def get_settings(self) -> Dict[str, Any]:
        """Get current settings as dictionary"""
        return {
            'clip_duration': int(self.duration_slider.get()),
            'quality': self.quality_var.get(),
            'scene_detection': self.scene_detect_var.get(),
            'output_dir': self.output_var.get(),
            'project_name': self.project_var.get(),
            'naming_pattern': self.naming_var.get(),
            'resolve_integration': self.resolve_var.get()
        }
        
    def apply_settings(self, settings: Dict[str, Any]):
        """Apply settings from dictionary"""
        if 'clip_duration' in settings:
            self.duration_slider.set(settings['clip_duration'])
            self.duration_value.configure(text=f"{settings['clip_duration']}s")
        if 'quality' in settings:
            self.quality_var.set(settings['quality'])
        if 'scene_detection' in settings:
            self.scene_detect_var.set(settings['scene_detection'])
            self._on_scene_detect_toggle()
        if 'output_dir' in settings:
            self.output_var.set(settings['output_dir'])
        if 'project_name' in settings:
            self.project_var.set(settings['project_name'])
        if 'naming_pattern' in settings:
            self.naming_var.set(settings['naming_pattern'])
        if 'resolve_integration' in settings:
            self.resolve_var.set(settings['resolve_integration'])

