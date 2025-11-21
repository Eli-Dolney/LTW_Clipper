#!/usr/bin/env python3
"""
Professional Video Splitter GUI - Cross-platform (macOS/Windows)
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import sys
from pathlib import Path
from typing import List, Optional
import json

# Try to import drag & drop support (fallback if not available)
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    # Fallback to regular tkinter
    import tkinter as tk
    TkinterDnD = tk.Tk
    DND_AVAILABLE = False

# Add current directory to path for imports
sys.path.append('.')

from video_splitter import VideoSplitter

class VideoSplitterGUI:
    def __init__(self):
        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Create main window
        self.root = TkinterDnD.Tk()
        self.root.title("🎬 LTW Video Splitter Pro")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # Check drag & drop availability
        if not DND_AVAILABLE:
            print("ℹ️  Drag & drop not available - use browse button instead")

        # Initialize variables
        self.selected_files: List[Path] = []
        self.is_processing = False
        self.current_splitter: Optional[VideoSplitter] = None

        self.setup_ui()
        self.center_window()

    def setup_ui(self):
        """Setup the main UI components"""
        # Create main container
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Header
        self.create_header()

        # File selection area
        self.create_file_selection()

        # Settings panel
        self.create_settings_panel()

        # Progress area
        self.create_progress_area()

        # Control buttons
        self.create_control_buttons()

        # Status bar
        self.create_status_bar()

    def create_header(self):
        """Create header with title and logo"""
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text="🎬 LTW Video Splitter Pro",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=10)

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Professional video splitting for YouTube creators",
            font=ctk.CTkFont(size=12)
        )
        subtitle_label.pack()

    def create_file_selection(self):
        """Create file selection area with drag & drop"""
        file_frame = ctk.CTkFrame(self.main_frame)
        file_frame.pack(fill="x", pady=(0, 10))

        # Title
        file_title = ctk.CTkLabel(
            file_frame,
            text="📁 Video Files",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        file_title.pack(pady=(10, 5))

        # Drop zone
        self.drop_zone = ctk.CTkFrame(
            file_frame,
            fg_color=("gray85", "gray20"),
            border_width=2,
            border_color=("gray70", "gray30")
        )
        self.drop_zone.pack(fill="x", padx=10, pady=(0, 10))

        self.drop_label = ctk.CTkLabel(
            self.drop_zone,
            text="📂 Drag & drop video files here\nor click to browse",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray60")
        )
        self.drop_label.pack(pady=20)

        # Make drop zone clickable
        self.drop_zone.bind("<Button-1>", lambda e: self.browse_files())

        # Enable drag & drop if available
        if DND_AVAILABLE:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind('<<Drop>>', self.on_drop)
        else:
            # Update label to indicate drag & drop not available
            self.drop_label.configure(text="📂 Click to browse video files\n(drag & drop not available)")

        # File list
        self.file_listbox = ctk.CTkScrollableFrame(
            file_frame,
            height=100
        )
        self.file_listbox.pack(fill="x", padx=10, pady=(0, 10))

        # File count label
        self.file_count_label = ctk.CTkLabel(
            file_frame,
            text="No files selected",
            font=ctk.CTkFont(size=11)
        )
        self.file_count_label.pack(pady=(0, 10))

    def create_settings_panel(self):
        """Create settings panel with all options"""
        settings_frame = ctk.CTkFrame(self.main_frame)
        settings_frame.pack(fill="x", pady=(0, 10))

        settings_title = ctk.CTkLabel(
            settings_frame,
            text="⚙️ Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        settings_title.pack(pady=(10, 5))

        # Create settings grid
        settings_grid = ctk.CTkFrame(settings_frame, fg_color="transparent")
        settings_grid.pack(fill="x", padx=10, pady=(0, 10))

        # Row 1: Duration and Quality
        row1 = ctk.CTkFrame(settings_grid, fg_color="transparent")
        row1.pack(fill="x", pady=5)

        ctk.CTkLabel(row1, text="Duration (seconds):", width=150).pack(side="left", padx=(0, 10))
        self.duration_var = ctk.StringVar(value="30")
        self.duration_entry = ctk.CTkEntry(row1, textvariable=self.duration_var, width=80)
        self.duration_entry.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(row1, text="Quality:", width=60).pack(side="left", padx=(0, 10))
        self.quality_var = ctk.StringVar(value="youtube_hd")
        self.quality_menu = ctk.CTkOptionMenu(
            row1,
            values=["youtube_sd", "youtube_hd", "youtube_4k", "original"],
            variable=self.quality_var,
            width=120
        )
        self.quality_menu.pack(side="left")

        # Row 2: Naming and Project
        row2 = ctk.CTkFrame(settings_grid, fg_color="transparent")
        row2.pack(fill="x", pady=5)

        ctk.CTkLabel(row2, text="Project Name:", width=150).pack(side="left", padx=(0, 10))
        self.project_var = ctk.StringVar(value="")
        self.project_entry = ctk.CTkEntry(row2, textvariable=self.project_var, width=200)
        self.project_entry.pack(side="left", padx=(0, 20))

        # Row 3: Advanced options
        row3 = ctk.CTkFrame(settings_grid, fg_color="transparent")
        row3.pack(fill="x", pady=5)

        # Scene detection
        self.scene_detect_var = ctk.BooleanVar(value=False)
        self.scene_checkbox = ctk.CTkCheckBox(
            row3,
            text="🎬 Scene Detection (AI-powered splitting)",
            variable=self.scene_detect_var
        )
        self.scene_checkbox.pack(side="left", padx=(0, 20))

        # Batch mode
        self.batch_var = ctk.BooleanVar(value=False)
        self.batch_checkbox = ctk.CTkCheckBox(
            row3,
            text="📦 Batch Mode (process directory)",
            variable=self.batch_var,
            command=self.toggle_batch_mode
        )
        self.batch_checkbox.pack(side="left", padx=(0, 20))

        # DaVinci Resolve
        self.resolve_var = ctk.BooleanVar(value=True)
        self.resolve_checkbox = ctk.CTkCheckBox(
            row3,
            text="🎭 DaVinci Resolve Project",
            variable=self.resolve_var
        )
        self.resolve_checkbox.pack(side="left")

        # Row 4: Output directory
        row4 = ctk.CTkFrame(settings_grid, fg_color="transparent")
        row4.pack(fill="x", pady=5)

        ctk.CTkLabel(row4, text="Output Directory:", width=150).pack(side="left", padx=(0, 10))
        self.output_var = ctk.StringVar(value=str(Path.home() / "Desktop" / "clips"))
        self.output_entry = ctk.CTkEntry(row4, textvariable=self.output_var)
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.output_button = ctk.CTkButton(row4, text="📁 Browse", width=80, command=self.browse_output)
        self.output_button.pack(side="right")

    def create_progress_area(self):
        """Create progress tracking area"""
        progress_frame = ctk.CTkFrame(self.main_frame)
        progress_frame.pack(fill="x", pady=(0, 10))

        progress_title = ctk.CTkLabel(
            progress_frame,
            text="📊 Progress",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        progress_title.pack(pady=(10, 5))

        # Overall progress
        self.overall_progress = ctk.CTkProgressBar(progress_frame, width=400)
        self.overall_progress.pack(pady=(0, 10))
        self.overall_progress.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Ready to process videos",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.pack(pady=(0, 10))

        # Current file progress
        self.file_progress = ctk.CTkProgressBar(progress_frame, width=400)
        self.file_progress.pack(pady=(0, 5))
        self.file_progress.set(0)

        self.file_progress_label = ctk.CTkLabel(
            progress_frame,
            text="",
            font=ctk.CTkFont(size=11)
        )
        self.file_progress_label.pack()

    def create_control_buttons(self):
        """Create control buttons"""
        button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 10))

        # Button container
        button_container = ctk.CTkFrame(button_frame, fg_color="transparent")
        button_container.pack(anchor="center")

        self.start_button = ctk.CTkButton(
            button_container,
            text="🚀 Start Processing",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self.start_processing
        )
        self.start_button.pack(side="left", padx=10)

        self.stop_button = ctk.CTkButton(
            button_container,
            text="⏹️ Stop",
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color="transparent",
            border_width=2,
            state="disabled",
            command=self.stop_processing
        )
        self.stop_button.pack(side="left", padx=10)

        self.preview_button = ctk.CTkButton(
            button_container,
            text="👀 Preview",
            font=ctk.CTkFont(size=14),
            height=40,
            command=self.preview_clips
        )
        self.preview_button.pack(side="left", padx=10)

    def create_status_bar(self):
        """Create status bar"""
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Ready",
            font=ctk.CTkFont(size=11),
            text_color=("gray60", "gray50")
        )
        self.status_label.pack(anchor="w", padx=10, pady=(0, 10))

    def toggle_batch_mode(self):
        """Toggle batch mode settings"""
        if self.batch_var.get():
            # In batch mode, disable individual file selection
            self.drop_zone.configure(state="disabled")
            self.drop_label.configure(text="📂 Batch mode: Will process all videos in selected directory")
            self.selected_files = []
            self.update_file_list()
        else:
            # Return to individual file selection
            self.drop_zone.configure(state="normal")
            self.drop_label.configure(text="📂 Drag & drop video files here\nor click to browse")
            self.update_file_list()

    def browse_files(self):
        """Browse for video files"""
        if self.batch_var.get():
            # Batch mode - select directory
            directory = filedialog.askdirectory(title="Select directory with videos")
            if directory:
                self.selected_files = [Path(directory)]
                self.update_file_list()
        else:
            # Individual files mode
            files = filedialog.askopenfilenames(
                title="Select video files",
                filetypes=[
                    ("Video files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm"),
                    ("All files", "*.*")
                ]
            )
            if files:
                self.selected_files = [Path(f) for f in files]
                self.update_file_list()

    def browse_output(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(title="Select output directory")
        if directory:
            self.output_var.set(directory)

    def on_drop(self, event):
        """Handle file drop"""
        if not DND_AVAILABLE or self.batch_var.get():
            return  # Ignore drops if not available or in batch mode

        files = self.root.tk.splitlist(event.data)
        video_files = []

        for file in files:
            path = Path(file)
            if path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']:
                video_files.append(path)
            elif path.is_dir():
                # If a directory is dropped, add all video files from it
                for video_file in path.rglob('*'):
                    if video_file.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']:
                        video_files.append(video_file)

        if video_files:
            self.selected_files = video_files
            self.update_file_list()

    def update_file_list(self):
        """Update the file list display"""
        # Clear existing file list
        for widget in self.file_listbox.winfo_children():
            widget.destroy()

        if not self.selected_files:
            self.file_count_label.configure(text="No files selected")
            return

        if self.batch_var.get() and len(self.selected_files) == 1 and self.selected_files[0].is_dir():
            # Batch mode - show directory info
            directory = self.selected_files[0]
            video_files = list(directory.rglob('*'))
            video_files = [f for f in video_files if f.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']]

            file_info = ctk.CTkLabel(
                self.file_listbox,
                text=f"📂 {directory.name}\n{video_files.__len__()} video files found",
                font=ctk.CTkFont(size=12),
                justify="left"
            )
            file_info.pack(anchor="w", padx=10, pady=2)
            self.file_count_label.configure(text=f"Directory: {len(video_files)} videos")
        else:
            # Individual files mode
            for file in self.selected_files:
                file_info = ctk.CTkLabel(
                    self.file_listbox,
                    text=f"🎬 {file.name}",
                    font=ctk.CTkFont(size=11),
                    justify="left"
                )
                file_info.pack(anchor="w", padx=10, pady=2)
            self.file_count_label.configure(text=f"{len(self.selected_files)} files selected")

    def preview_clips(self):
        """Preview what clips will be created"""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select video files first")
            return

        try:
            # Create a temporary splitter to analyze files
            temp_splitter = VideoSplitter(
                clip_duration=int(self.duration_var.get()),
                scene_detection=self.scene_detect_var.get(),
                quality=self.quality_var.get()
            )

            preview_info = []
            total_clips = 0

            for file_path in self.selected_files:
                if file_path.is_file():
                    clips = temp_splitter.estimate_clips(file_path)
                    preview_info.append(f"🎬 {file_path.name}: {clips} clips")
                    total_clips += clips
                elif file_path.is_dir():
                    # Batch mode directory
                    video_files = list(file_path.rglob('*'))
                    video_files = [f for f in video_files if f.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']]

                    for video_file in video_files:
                        clips = temp_splitter.estimate_clips(video_file)
                        total_clips += clips

                    preview_info.append(f"📂 {file_path.name}: {len(video_files)} videos → {total_clips} total clips")

            preview_text = "\n".join(preview_info)
            preview_text += f"\n\n📊 Total: {total_clips} clips will be created"

            # Show preview dialog
            preview_window = ctk.CTkToplevel(self.root)
            preview_window.title("Clip Preview")
            preview_window.geometry("500x400")

            ctk.CTkLabel(preview_window, text="📋 Clip Creation Preview", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

            preview_textbox = ctk.CTkTextbox(preview_window, wrap="word")
            preview_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            preview_textbox.insert("0.0", preview_text)
            preview_textbox.configure(state="disabled")

            ctk.CTkButton(preview_window, text="OK", command=preview_window.destroy).pack(pady=(0, 10))

        except Exception as e:
            messagebox.showerror("Preview Error", f"Could not preview clips: {str(e)}")

    def start_processing(self):
        """Start video processing"""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select video files first")
            return

        if self.is_processing:
            return

        # Validate inputs
        try:
            duration = int(self.duration_var.get())
            if duration <= 0:
                raise ValueError("Duration must be positive")
        except ValueError:
            messagebox.showerror("Invalid Duration", "Please enter a valid positive number for duration")
            return

        # Disable controls
        self.start_button.configure(state="disabled", text="🔄 Processing...")
        self.stop_button.configure(state="normal")
        self.preview_button.configure(state="disabled")
        self.is_processing = True

        # Start processing in background thread
        processing_thread = threading.Thread(target=self.process_videos)
        processing_thread.daemon = True
        processing_thread.start()

    def stop_processing(self):
        """Stop video processing"""
        if self.current_splitter:
            self.is_processing = False
            self.status_label.configure(text="⏹️ Stopping... (progress will be saved)")
            self.start_button.configure(state="normal", text="🚀 Start Processing")
            self.stop_button.configure(state="disabled")

    def process_videos(self):
        """Process videos in background thread"""
        try:
            # Create splitter
            self.current_splitter = VideoSplitter(
                output_dir=self.output_var.get(),
                clip_duration=int(self.duration_var.get()),
                quality=self.quality_var.get(),
                resolve_integration=self.resolve_var.get(),
                project_name=self.project_var.get() or None,
                scene_detection=self.scene_detect_var.get(),
                batch_mode=self.batch_var.get()
            )

            if self.batch_var.get():
                # Batch processing
                input_dir = str(self.selected_files[0]) if self.selected_files else "."
                total_clips = self.current_splitter.split_all_videos()
                self.root.after(0, lambda: self.on_processing_complete(total_clips))
            else:
                # Individual file processing
                total_clips = 0
                for i, video_file in enumerate(self.selected_files):
                    if not self.is_processing:
                        break

                    self.root.after(0, lambda idx=i, total=len(self.selected_files): self.update_progress(idx, total, f"Processing {self.selected_files[idx].name}"))

                    try:
                        clips_created = self.current_splitter.split_video(video_file)
                        total_clips += clips_created
                    except Exception as e:
                        print(f"Error processing {video_file.name}: {e}")

                self.root.after(0, lambda: self.on_processing_complete(total_clips))

        except Exception as e:
            self.root.after(0, lambda: self.on_processing_error(str(e)))

    def update_progress(self, current, total, message):
        """Update progress display"""
        progress = (current + 1) / total
        self.overall_progress.set(progress)
        self.progress_label.configure(text=f"{current + 1}/{total}: {message}")
        self.status_label.configure(text=f"Processing: {message}")

    def on_processing_complete(self, total_clips):
        """Handle processing completion"""
        self.is_processing = False
        self.overall_progress.set(1.0)
        self.progress_label.configure(text="✅ Processing complete!")
        self.status_label.configure(text=f"✅ Created {total_clips} clips successfully")

        # Re-enable controls
        self.start_button.configure(state="normal", text="🚀 Start Processing")
        self.stop_button.configure(state="disabled")
        self.preview_button.configure(state="normal")

        # Show success message
        messagebox.showinfo("Complete", f"Successfully created {total_clips} video clips!")

    def on_processing_error(self, error_msg):
        """Handle processing error"""
        self.is_processing = False
        self.status_label.configure(text=f"❌ Error: {error_msg}")

        # Re-enable controls
        self.start_button.configure(state="normal", text="🚀 Start Processing")
        self.stop_button.configure(state="disabled")
        self.preview_button.configure(state="normal")

        messagebox.showerror("Processing Error", f"An error occurred: {error_msg}")

    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = VideoSplitterGUI()
    app.run()
