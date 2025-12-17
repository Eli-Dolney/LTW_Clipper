"""
LTW Video Editor Pro - File Picker Component
Drag-and-drop file selection with preview
"""

import customtkinter as ctk
from tkinter import filedialog
from typing import Callable, List, Optional
from pathlib import Path
import sys
import os

from ..theme import theme, get_font

# Try to import drag & drop support
try:
    from tkinterdnd2 import DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


class FileCard(ctk.CTkFrame):
    """Card displaying a selected file"""
    
    def __init__(self, parent, filepath: Path, on_remove: Optional[Callable] = None, **kwargs):
        super().__init__(
            parent,
            fg_color=theme.colors.bg_tertiary,
            corner_radius=8,
            height=50,
            **kwargs
        )
        
        self.filepath = filepath
        self.on_remove = on_remove
        self.pack_propagate(False)
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Create file card widgets"""
        # Icon
        icon_label = ctk.CTkLabel(
            self,
            text="🎬",
            font=get_font("lg"),
            width=40
        )
        icon_label.pack(side="left", padx=(theme.spacing.sm, 0))
        
        # File info
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=theme.spacing.sm)
        
        name_label = ctk.CTkLabel(
            info_frame,
            text=self.filepath.name[:40] + ("..." if len(self.filepath.name) > 40 else ""),
            font=get_font("sm"),
            text_color=theme.colors.text_primary,
            anchor="w"
        )
        name_label.pack(anchor="w")
        
        # Get file size
        try:
            size_mb = self.filepath.stat().st_size / (1024 * 1024)
            size_text = f"{size_mb:.1f} MB"
        except:
            size_text = "Unknown size"
            
        size_label = ctk.CTkLabel(
            info_frame,
            text=size_text,
            font=get_font("xs"),
            text_color=theme.colors.text_muted,
            anchor="w"
        )
        size_label.pack(anchor="w")
        
        # Remove button
        remove_btn = ctk.CTkButton(
            self,
            text="✕",
            font=get_font("sm"),
            width=30,
            height=30,
            fg_color="transparent",
            hover_color=theme.colors.error,
            text_color=theme.colors.text_muted,
            command=self._on_remove
        )
        remove_btn.pack(side="right", padx=theme.spacing.sm)
        
    def _on_remove(self):
        """Handle remove button click"""
        if self.on_remove:
            self.on_remove(self.filepath)


class FilePicker(ctk.CTkFrame):
    """Professional file picker with drag-and-drop"""
    
    def __init__(self, parent, on_files_changed: Optional[Callable] = None, 
                 multiple: bool = True, **kwargs):
        super().__init__(
            parent,
            fg_color="transparent",
            **kwargs
        )
        
        self.on_files_changed = on_files_changed
        self.multiple = multiple
        self.selected_files: List[Path] = []
        self.file_cards: List[FileCard] = []
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Create file picker widgets"""
        # Drop zone
        self.drop_zone = ctk.CTkFrame(
            self,
            fg_color=theme.colors.bg_tertiary,
            border_width=2,
            border_color=theme.colors.border_default,
            corner_radius=theme.spacing.card_radius,
            height=120
        )
        self.drop_zone.pack(fill="x", pady=(0, theme.spacing.md))
        self.drop_zone.pack_propagate(False)
        
        # Drop zone content
        drop_content = ctk.CTkFrame(self.drop_zone, fg_color="transparent")
        drop_content.place(relx=0.5, rely=0.5, anchor="center")
        
        drop_icon = ctk.CTkLabel(
            drop_content,
            text="📂",
            font=get_font("3xl")
        )
        drop_icon.pack()
        
        drop_text = ctk.CTkLabel(
            drop_content,
            text="Drag & drop video files here" if DND_AVAILABLE else "Click to select video files",
            font=get_font("md"),
            text_color=theme.colors.text_secondary
        )
        drop_text.pack(pady=(theme.spacing.xs, 0))
        
        drop_subtext = ctk.CTkLabel(
            drop_content,
            text="or click to browse • MP4, MOV, MKV, AVI, WebM",
            font=get_font("xs"),
            text_color=theme.colors.text_muted
        )
        drop_subtext.pack()
        
        # Make drop zone clickable
        self.drop_zone.bind("<Button-1>", lambda e: self.browse_files())
        drop_content.bind("<Button-1>", lambda e: self.browse_files())
        drop_icon.bind("<Button-1>", lambda e: self.browse_files())
        drop_text.bind("<Button-1>", lambda e: self.browse_files())
        drop_subtext.bind("<Button-1>", lambda e: self.browse_files())
        
        # Enable drag & drop if available
        if DND_AVAILABLE:
            try:
                self.drop_zone.drop_target_register(DND_FILES)
                self.drop_zone.dnd_bind('<<Drop>>', self._on_drop)
            except:
                pass  # DND registration failed
        
        # Hover effects
        self.drop_zone.bind("<Enter>", self._on_hover_enter)
        self.drop_zone.bind("<Leave>", self._on_hover_leave)
        
        # File list container
        self.file_list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            height=150
        )
        self.file_list_frame.pack(fill="both", expand=True)
        
        # File count label
        self.count_label = ctk.CTkLabel(
            self,
            text="No files selected",
            font=get_font("sm"),
            text_color=theme.colors.text_muted
        )
        self.count_label.pack(anchor="w", pady=(theme.spacing.sm, 0))
        
    def _on_hover_enter(self, event):
        """Handle mouse enter on drop zone"""
        self.drop_zone.configure(
            border_color=theme.colors.accent_primary,
            fg_color=theme.colors.bg_hover
        )
        
    def _on_hover_leave(self, event):
        """Handle mouse leave from drop zone"""
        self.drop_zone.configure(
            border_color=theme.colors.border_default,
            fg_color=theme.colors.bg_tertiary
        )
        
    def _on_drop(self, event):
        """Handle file drop"""
        if not DND_AVAILABLE:
            return
            
        # Parse dropped files
        try:
            files = self.winfo_toplevel().tk.splitlist(event.data)
        except:
            files = event.data.split()
            
        self._add_files(files)
        
    def browse_files(self):
        """Open file browser dialog"""
        filetypes = [
            ("Video files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm"),
            ("All files", "*.*")
        ]
        
        if self.multiple:
            files = filedialog.askopenfilenames(
                title="Select video files",
                filetypes=filetypes
            )
        else:
            file = filedialog.askopenfilename(
                title="Select video file",
                filetypes=filetypes
            )
            files = [file] if file else []
            
        if files:
            self._add_files(files)
            
    def _add_files(self, files):
        """Add files to selection"""
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm'}
        
        for file in files:
            path = Path(file)
            if path.suffix.lower() in video_extensions and path not in self.selected_files:
                self.selected_files.append(path)
                
        self._update_file_list()
        self._notify_change()
        
    def _remove_file(self, filepath: Path):
        """Remove file from selection"""
        if filepath in self.selected_files:
            self.selected_files.remove(filepath)
        self._update_file_list()
        self._notify_change()
        
    def _update_file_list(self):
        """Update file list display"""
        # Clear existing cards
        for card in self.file_cards:
            card.destroy()
        self.file_cards.clear()
        
        # Create new cards
        for filepath in self.selected_files:
            card = FileCard(
                self.file_list_frame,
                filepath=filepath,
                on_remove=self._remove_file
            )
            card.pack(fill="x", pady=2)
            self.file_cards.append(card)
            
        # Update count label
        count = len(self.selected_files)
        if count == 0:
            self.count_label.configure(text="No files selected")
        elif count == 1:
            self.count_label.configure(text="1 file selected")
        else:
            self.count_label.configure(text=f"{count} files selected")
            
    def _notify_change(self):
        """Notify parent of file selection change"""
        if self.on_files_changed:
            self.on_files_changed(self.selected_files)
            
    def get_files(self) -> List[Path]:
        """Get list of selected files"""
        return self.selected_files.copy()
        
    def clear(self):
        """Clear all selected files"""
        self.selected_files.clear()
        self._update_file_list()
        self._notify_change()

