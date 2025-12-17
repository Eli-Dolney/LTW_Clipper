#!/usr/bin/env python3
"""
Video Splitter Script
Splits downloaded videos into 30-second clips
"""

import os
import sys
from pathlib import Path
from moviepy import VideoFileClip
import argparse
from typing import List, Optional, Dict, Any
import re
from tqdm import tqdm
import subprocess
import json
from datetime import datetime
import xml.etree.ElementTree as ET
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim


class VideoSplitter:
    def __init__(self, input_dir: str = ".", output_dir: str = None, clip_duration: int = 30,
                 naming_pattern: str = "{name}_part_{num:03d}", quality: str = "youtube_hd",
                 resolve_integration: bool = True, project_name: str = None,
                 scene_detection: bool = False, min_scene_duration: int = 10,
                 batch_mode: bool = False, resume_batch: bool = False):
        """
        Initialize the VideoSplitter

        Args:
            input_dir: Directory containing videos to split
            output_dir: Directory to save the clips (default: Desktop/clips)
            clip_duration: Duration of each clip in seconds
            naming_pattern: Pattern for clip naming (use {name}, {num}, {duration}, {timestamp})
            quality: Video quality ('youtube_sd', 'youtube_hd', 'youtube_4k', 'original')
            resolve_integration: Generate DaVinci Resolve project files
            project_name: Name for Resolve project (auto-generated if None)
            scene_detection: Use intelligent scene detection for splitting
            min_scene_duration: Minimum duration for detected scenes (seconds)
            batch_mode: Process all videos in input directory
            resume_batch: Resume interrupted batch processing
        """
        self.input_dir = Path(input_dir)

        # Set output directory to Desktop/clips if not specified
        if output_dir is None:
            desktop = Path.home() / "Desktop"
            self.output_dir = desktop / "clips"
        else:
            self.output_dir = Path(output_dir)

        self.clip_duration = clip_duration
        self.naming_pattern = naming_pattern
        self.quality = quality
        self.scene_detection = scene_detection
        self.min_scene_duration = min_scene_duration
        self.batch_mode = batch_mode
        self.resume_batch = resume_batch

        # Batch processing state
        self.batch_progress_file = Path(self.output_dir) / "batch_progress.json"
        self.processed_videos = set()
        self.resolve_integration = resolve_integration

        # Auto-generate project name if not provided
        if project_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.project_name = f"YouTube_Project_{timestamp}"
        else:
            self.project_name = project_name

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True)

        # Create subdirectories for professional organization
        self.clips_dir = self.output_dir / "clips"
        self.metadata_dir = self.output_dir / "metadata"
        self.resolve_dir = self.output_dir / "resolve_project"

        for dir_path in [self.clips_dir, self.metadata_dir, self.resolve_dir]:
            dir_path.mkdir(exist_ok=True)

        # Supported video formats
        self.supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm'}

        # YouTube-optimized quality settings
        self.quality_settings = {
            'youtube_sd': {
                'bitrate': '2000k',
                'resolution': '854x480',
                'preset': 'fast',
                'description': 'YouTube SD (480p)'
            },
            'youtube_hd': {
                'bitrate': '5000k',
                'resolution': '1920x1080',
                'preset': 'fast',
                'description': 'YouTube HD (1080p)'
            },
            'youtube_4k': {
                'bitrate': '15000k',
                'resolution': '3840x2160',
                'preset': 'slow',
                'description': 'YouTube 4K (2160p)'
            },
            'original': {
                'bitrate': None,
                'resolution': None,
                'preset': 'fast',
                'description': 'Original quality'
            }
        }

        # Track processed clips for Resolve integration
        self.clip_metadata = []
    
    def clean_filename(self, filename: str) -> str:
        """Clean filename for better naming conventions"""
        # Remove special characters and replace with underscores
        cleaned = re.sub(r'[^\w\s-]', '', filename)
        # Replace spaces with underscores
        cleaned = re.sub(r'\s+', '_', cleaned)
        # Remove multiple underscores
        cleaned = re.sub(r'_+', '_', cleaned)
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        return cleaned

    def detect_scenes(self, video_path: Path, threshold: float = 0.3) -> List[float]:
        """
        Detect scene changes in video using frame difference analysis

        Args:
            video_path: Path to video file
            threshold: Similarity threshold for scene detection (0-1, lower = more sensitive)

        Returns:
            List of timestamps where scene changes occur
        """
        print("🎬 Analyzing video for scene changes...")

        # Open video with OpenCV
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print("❌ Could not open video for scene detection")
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        scene_changes = []

        # Sample every 30th frame for performance
        sample_rate = 30
        prev_frame = None

        with tqdm(total=total_frames//sample_rate, desc="Scene analysis") as pbar:
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Convert to grayscale and resize for faster processing
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (320, 180))  # Smaller size for performance

                if prev_frame is not None and frame_count % sample_rate == 0:
                    # Calculate structural similarity
                    try:
                        similarity = ssim(prev_frame, gray)
                        if similarity < threshold:  # Scene change detected
                            timestamp = frame_count / fps
                            if timestamp >= self.min_scene_duration:
                                scene_changes.append(timestamp)
                    except:
                        pass  # Skip frames that cause SSIM errors

                prev_frame = gray
                frame_count += 1

                if frame_count % sample_rate == 0:
                    pbar.update(1)

        cap.release()

        # Filter out scenes that are too close together
        filtered_changes = []
        min_gap = 30  # Minimum 30 seconds between scenes
        last_scene = 0

        for scene_time in scene_changes:
            if scene_time - last_scene >= min_gap:
                filtered_changes.append(scene_time)
                last_scene = scene_time

        print(f"✅ Detected {len(filtered_changes)} scene changes")
        return filtered_changes

    def save_batch_progress(self, processed_videos: List[str]):
        """Save batch processing progress to resume later"""
        progress_data = {
            'processed_videos': processed_videos,
            'timestamp': datetime.now().isoformat(),
            'settings': {
                'clip_duration': self.clip_duration,
                'quality': self.quality,
                'scene_detection': self.scene_detection,
                'naming_pattern': self.naming_pattern
            }
        }

        with open(self.batch_progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)

    def load_batch_progress(self) -> Dict:
        """Load batch processing progress for resume"""
        if not self.batch_progress_file.exists():
            return {'processed_videos': []}

        try:
            with open(self.batch_progress_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {'processed_videos': []}

    def process_batch(self) -> int:
        """Process all videos in batch mode with resume capability"""
        if not self.batch_mode:
            raise ValueError("Batch mode not enabled. Use batch_mode=True")

        # Get all video files
        all_videos = self.get_video_files()
        if not all_videos:
            print("❌ No video files found in input directory")
            return 0

        # Load previous progress if resuming
        if self.resume_batch:
            progress_data = self.load_batch_progress()
            processed_names = set(progress_data.get('processed_videos', []))
            print(f"📋 Resuming batch: {len(processed_names)} videos already processed")
        else:
            processed_names = set()
            # Clean up old progress file
            if self.batch_progress_file.exists():
                self.batch_progress_file.unlink()

        # Filter out already processed videos
        videos_to_process = [v for v in all_videos if v.name not in processed_names]

        if not videos_to_process:
            print("✅ All videos already processed!")
            return len(processed_names)

        print(f"🎬 Processing {len(videos_to_process)} videos in batch mode")
        print(f"📁 Output: {self.output_dir}")
        print()

        total_clips_created = 0
        processed_names_list = list(processed_names)

        try:
            for i, video_file in enumerate(videos_to_process, 1):
                print(f"\n🎥 [{i}/{len(videos_to_process)}] Processing: {video_file.name}")

                try:
                    # Process this video
                    clips_created = self.split_video(video_file)
                    total_clips_created += clips_created

                    # Mark as processed
                    processed_names_list.append(video_file.name)
                    self.save_batch_progress(processed_names_list)

                    print(f"✅ Completed: {clips_created} clips created")

                except Exception as e:
                    print(f"❌ Failed to process {video_file.name}: {str(e)}")
                    # Continue with next video but save progress
                    self.save_batch_progress(processed_names_list)
                    continue

        except KeyboardInterrupt:
            print("\n⏸️  Batch processing interrupted. Progress saved.")
            print(f"📋 To resume: python your_script.py --batch --resume")
            return total_clips_created

        # Clean up progress file on successful completion
        if self.batch_progress_file.exists():
            self.batch_progress_file.unlink()

        print(f"\n🎉 Batch processing complete!")
        print(f"📊 Total: {len(processed_names_list)} videos processed, {total_clips_created} clips created")

        return total_clips_created

    def estimate_clips(self, video_path: Path) -> int:
        """Estimate number of clips that will be created from a video"""
        try:
            video = VideoFileClip(str(video_path))
            duration = video.duration
            video.close()

            if self.scene_detection:
                # For scene detection, we'll estimate based on typical scene length
                # This is just an estimate since we don't want to run full scene detection for preview
                avg_scene_length = 45 if self.clip_duration > 60 else 30  # Adaptive estimate
                return max(1, int(duration / avg_scene_length))
            else:
                # Time-based splitting
                return max(1, int(duration / self.clip_duration))

        except Exception:
            return 1  # Default to 1 clip if we can't analyze

    def get_video_files(self) -> List[Path]:
        """Get all video files from the input directory"""
        video_files = []
        
        if not self.input_dir.exists():
            print(f"Error: Input directory '{self.input_dir}' does not exist.")
            return video_files
        
        for file_path in self.input_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                video_files.append(file_path)
        
        return video_files
    
    def split_video(self, video_path: Path) -> int:
        """
        Split a single video into clips
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Number of clips created
        """
        try:
            print(f"Processing: {video_path.name}")
            
            # Load the video
            video = VideoFileClip(str(video_path))
            duration = video.duration
            
            # Calculate number of clips
            num_clips = int(duration // self.clip_duration)
            if duration % self.clip_duration > 0:
                num_clips += 1
            
            print(f"  Duration: {duration:.2f} seconds")

            # Detect scenes if enabled
            if self.scene_detection:
                scene_changes = self.detect_scenes(video_path)
                if scene_changes:
                    # Use scene boundaries for splitting
                    clip_boundaries = [0] + scene_changes + [duration]
                    clip_times = []
                    for i in range(len(clip_boundaries) - 1):
                        start = clip_boundaries[i]
                        end = clip_boundaries[i + 1]
                        if end - start >= self.min_scene_duration:
                            clip_times.append((start, end))

                    print(f"  Creating {len(clip_times)} scene-based clips")
                else:
                    # Fall back to time-based splitting
                    print(f"  No clear scenes detected, using {self.clip_duration}s intervals")
                    clip_times = []
                    for i in range(num_clips):
                        start_time = i * self.clip_duration
                        end_time = min((i + 1) * self.clip_duration, duration)
                        clip_times.append((start_time, end_time))
            else:
                # Standard time-based splitting
                print(f"  Creating {num_clips} clips of {self.clip_duration} seconds each")
                clip_times = []
                for i in range(num_clips):
                    start_time = i * self.clip_duration
                    end_time = min((i + 1) * self.clip_duration, duration)
                    clip_times.append((start_time, end_time))

            # Clean the base filename
            base_name = self.clean_filename(video_path.stem)
            
            # Create clips with progress bar
            clips_created = 0
            for i, (start_time, end_time) in enumerate(tqdm(clip_times, desc=f"Creating clips", unit="clip")):
                try:
                    segment_duration = max(0.001, end_time - start_time)
                    
                    # Generate timestamp for professional naming
                    start_time_formatted = "02d"
                    end_time_formatted = "02d"

                    # Generate output filename using naming pattern
                    output_filename = self.naming_pattern.format(
                        name=base_name,
                        num=i+1,
                        duration=self.clip_duration,
                        timestamp=start_time_formatted,
                        project=self.project_name
                    ) + ".mp4"
                    output_path = self.clips_dir / output_filename
                    
                    # Build ffmpeg command ensuring audio is always encoded
                    quality_setting = self.quality_settings[self.quality]
                    ffmpeg_cmd = [
                        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-ss", f"{start_time:.3f}",
                        "-t", f"{segment_duration:.3f}",
                        "-i", str(video_path),
                        "-c:v", "libx264",
                        "-pix_fmt", "yuv420p",
                        "-preset", "fast",
                        "-c:a", "aac",
                        "-b:a", "160k",
                        "-ar", "44100",
                        "-ac", "2",
                    ]
                    # Apply quality controls
                    if quality_setting['bitrate']:
                        ffmpeg_cmd += ["-b:v", quality_setting['bitrate']]
                    if quality_setting['resolution']:
                        ffmpeg_cmd += ["-vf", f"scale={quality_setting['resolution']}"]
                    ffmpeg_cmd += [str(output_path)]
                    
                    try:
                        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    except subprocess.CalledProcessError as e:
                        # Retry with audio resample filter if first attempt fails
                        print(f"    Audio encode retry for clip {i+1}...")
                        retry_cmd = ffmpeg_cmd[:-1] + ["-af", "aresample=async=1:first_pts=0", str(output_path)]
                        subprocess.run(retry_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                    clips_created += 1

                    # Track metadata for Resolve integration
                    clip_info = {
                        'filename': output_filename,
                        'filepath': str(output_path),
                        'clip_number': i+1,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'timestamp': datetime.now().isoformat(),
                        'quality': self.quality,
                        'source_video': video_path.name
                    }
                    self.clip_metadata.append(clip_info)

                except Exception as clip_error:
                    print(f"    ✗ Error creating clip {i+1}: {str(clip_error)}")
                    # Continue with next clip instead of stopping
                    continue
            
            # Save metadata
            self._save_metadata(video_path.name)

            # Generate Resolve project files if enabled
            if self.resolve_integration:
                self._generate_resolve_project(video_path.name)

            # Clean up
            video.close()
            print(f"  ✓ Completed: {clips_created} clips created in {self.clips_dir}")
            if self.resolve_integration:
                print(f"  📁 Resolve project files saved to {self.resolve_dir}")
            print()
            return clips_created
            
        except Exception as e:
            print(f"  ✗ Error processing {video_path.name}: {str(e)}\n")
            return 0
    
    def split_all_videos(self) -> int:
        """Split all videos - uses batch processing if batch_mode is enabled"""
        if self.batch_mode:
            return self.process_batch()

        # Original single-pass processing for backward compatibility
        """
        Split all videos in the input directory (one video at a time)
        
        Returns:
            Total number of clips created
        """
        video_files = self.get_video_files()
        
        if not video_files:
            print(f"No video files found in '{self.input_dir}'")
            print(f"Supported formats: {', '.join(self.supported_formats)}")
            return 0
        
        print(f"Found {len(video_files)} video file(s) to process:")
        for video_file in video_files:
            print(f"  - {video_file.name}")
        print()
        
        total_clips = 0
        for i, video_file in enumerate(video_files, 1):
            print(f"Processing video {i}/{len(video_files)}:")
            clips_created = self.split_video(video_file)
            total_clips += clips_created
            
            if i < len(video_files):
                print("Moving to next video...\n")
        
        print(f"🎉 All done! Created {total_clips} clips in '{self.clips_dir}'")
        if self.resolve_integration and total_clips > 0:
            print(f"📁 DaVinci Resolve project files ready in '{self.resolve_dir}'")
        return total_clips

    def _save_metadata(self, source_video: str):
        """Save clip metadata to JSON file"""
        metadata_file = self.metadata_dir / f"{self.project_name}_metadata.json"

        metadata = {
            'project_name': self.project_name,
            'source_video': source_video,
            'total_clips': len(self.clip_metadata),
            'clip_duration': self.clip_duration,
            'quality': self.quality,
            'quality_description': self.quality_settings[self.quality]['description'],
            'created_at': datetime.now().isoformat(),
            'clips': self.clip_metadata
        }

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def _generate_resolve_project(self, source_video: str):
        """Generate DaVinci Resolve import files for easy project setup"""
        # Note: DaVinci Resolve .drp files are proprietary and complex.
        # We use Lua scripts instead, which is the recommended automation approach.

        # Create professional Lua import script
        batch_script = f"""-- DaVinci Resolve Professional Import Script
-- Generated by LTW Video Editor Pro - Opus Clip-Style Tool
-- Project: {self.project_name}
-- Source: {source_video}
-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

local function import_clips()
    -- Get project manager
    local projectManager = resolve:GetProjectManager()

    -- Create or get project
    local project = projectManager:GetCurrentProject()
    if not project then
        print("Creating new project: {self.project_name}")
        project = projectManager:CreateProject("{self.project_name}")
        if not project then
            print("ERROR: Failed to create project")
            return false
        end
    end

    -- Create timeline
    local mediaPool = project:GetMediaPool()
    local timeline = project:GetCurrentTimeline()
    
    if not timeline then
        print("Creating new timeline: {self.project_name}_Timeline")
        if mediaPool then
            timeline = mediaPool:CreateEmptyTimeline("{self.project_name}_Timeline")
        end
        
        if not timeline then
            print("ERROR: Failed to create timeline")
            return false
        end
    end

    -- Import clips in order
    local clips_imported = 0
    local clips = {{
"""

        for clip_info in self.clip_metadata:
            batch_script += f'        {{path="{clip_info["filepath"]}", name="{clip_info["filename"]}"}},\n'

        batch_script += f"""    }}

    print("Importing {len(self.clip_metadata)} clips...")

    for i, clipInfo in ipairs(clips) do
        print(string.format("Importing clip %d/%d: %%s", i, #clips, clipInfo.name))

        -- Import media
        local mediaPool = project:GetMediaPool()
        local clips = mediaPool:ImportMedia(clipInfo.path)

        if clips and #clips > 0 then
            -- Add to timeline using MediaPool method (Appends to CURRENT timeline)
            local appendedItems = mediaPool:AppendToTimeline(clips)
            
            if appendedItems then
                clips_imported = clips_imported + 1
            else
                print(string.format("WARNING: Failed to append %s to timeline", clipInfo.name))
            end
        else
            print(string.format("WARNING: Failed to import %s", clipInfo.name))
        end
    end

    print(string.format("SUCCESS: Imported %%d/%d clips", clips_imported, #clips))
    print("Project setup complete! Ready for professional editing.")
    return true
end

-- Execute import
local success = import_clips()
if success then
    print("\\n🎉 LTW Video Editor Pro - Import Complete!")
    print("Your clips are now ready in DaVinci Resolve for professional editing.")
else
    print("\\n❌ Import failed. Please check the console for error messages.")
end
"""

        lua_file = self.resolve_dir / f"{self.project_name}_import.lua"
        with open(lua_file, 'w', encoding='utf-8') as f:
            f.write(batch_script)

        # Create comprehensive README
        readme_content = f"""# 🎬 DaVinci Resolve Project: {self.project_name}

**Generated by LTW Video Editor Pro - Your Opus Clip-Style Tool**

## 📊 Project Overview
- **Source Video**: {source_video}
- **Total Clips**: {len(self.clip_metadata)}
- **Clip Duration**: {self.clip_duration} seconds each
- **Quality**: {self.quality_settings[self.quality]['description']}
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🚀 How to Import into DaVinci Resolve

### Step-by-Step Instructions:

1. **Open DaVinci Resolve**
2. **Go to the Workspace Menu**: `Workspace → Scripts → Run Script`
3. **Navigate to this folder**: Select `{self.project_name}_import.lua`
4. **Click "Run"**
5. **Watch the magic happen!** ✨

### What the Script Does:
- ✅ Creates a new project called "{self.project_name}"
- ✅ Sets up a professional timeline
- ✅ Imports all {len(self.clip_metadata)} clips in perfect order
- ✅ Provides progress feedback in the console

## 📁 File Structure
```
{self.project_name}_import.lua    # Professional import script
README.md                         # This documentation
../clips/                         # Your video clips
../metadata/                      # Detailed clip information
```

## 🎯 Next Steps After Import

### Professional Editing Workflow:
1. **Color Correction**: Use DaVinci Resolve's powerful color tools
2. **Audio Enhancement**: Clean up and enhance audio tracks
3. **Transitions**: Add professional transitions between clips
4. **Text & Graphics**: Add titles, lower thirds, and branding
5. **Export**: Render final videos for YouTube, TikTok, Instagram

### Content Strategy:
- **TikTok**: Focus on 15-30 second segments with hooks
- **Instagram Reels**: Vertical format, trending audio
- **YouTube Shorts**: Quick tutorials, tips, and highlights
- **LinkedIn**: Professional demonstrations and tutorials

## 🛠️ Troubleshooting

### If the script doesn't run:
- Make sure DaVinci Resolve is fully open
- Check that script execution is enabled in Resolve preferences
- Verify all clip files exist in the clips folder

### If clips don't import:
- Check file paths in the Lua script
- Ensure clips are in MP4 format
- Verify you have write permissions

## 📈 Pro Tips

- **Color Grading**: Start with Resolve's color page for professional looks
- **Audio Sweetening**: Use Fairlight page for voice enhancement
- **Stabilization**: Apply warp stabilizer for shaky footage
- **LUTs**: Apply cinematic looks from the gallery

## 🏆 Why LTW Video Editor Pro?

- **Local & Private**: No cloud uploads, your content stays on your machine
- **Professional Output**: DaVinci Resolve integration for studio-quality results
- **Batch Processing**: Handle multiple videos efficiently
- **GPU Acceleration**: Optimized for Mac M4 and NVIDIA GPUs
- **Free & Open Source**: No subscriptions or hidden fees

---
**Generated by LTW Video Editor Pro** 🚀
*Your complete Opus Clip-style video creation suite*
"""

        readme_file = self.resolve_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        print(f"  📁 Professional Resolve integration ready!")
        print(f"     Use the Lua script for automated import")


def main():
    parser = argparse.ArgumentParser(
        description="Split videos into 30-second clips",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python video_splitter.py                           # Split videos in current directory to Desktop/clips
  python video_splitter.py -i /path/to/videos        # Specify input directory
  python video_splitter.py -o /path/to/clips         # Specify output directory
  python video_splitter.py -d 60                     # Create 60-second clips
  python video_splitter.py -q high                   # High quality clips
  python video_splitter.py -n "{name}_clip_{num}"    # Custom naming pattern
  python video_splitter.py -i videos -o clips -d 45 -q high -n "{name}_segment_{num:02d}"  # All options
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        default='.',
        help='Input directory containing videos (default: current directory)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output directory for clips (default: Desktop/clips)'
    )
    
    parser.add_argument(
        '-d', '--duration',
        type=int,
        default=30,
        help='Duration of each clip in seconds (default: 30)'
    )
    
    parser.add_argument(
        '-n', '--naming',
        default='{name}_part_{num:03d}',
        help='Naming pattern for clips (use {name}, {num}, {duration}) (default: {name}_part_{num:03d})'
    )
    
    parser.add_argument(
        '-q', '--quality',
        choices=['youtube_sd', 'youtube_hd', 'youtube_4k', 'original'],
        default='youtube_hd',
        help='Video quality optimized for YouTube (default: youtube_hd)'
    )

    parser.add_argument(
        '--resolve',
        action='store_true',
        default=True,
        help='Generate DaVinci Resolve project files (default: enabled)'
    )

    parser.add_argument(
        '--project-name',
        default=None,
        help='Name for Resolve project (auto-generated if not specified)'
    )

    parser.add_argument(
        '--scene-detection',
        action='store_true',
        help='Use intelligent scene detection for splitting at natural boundaries'
    )

    parser.add_argument(
        '--min-scene-duration',
        type=int,
        default=10,
        help='Minimum duration for detected scenes in seconds (default: 10)'
    )

    parser.add_argument(
        '--batch',
        action='store_true',
        help='Process all videos in input directory (batch mode)'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume interrupted batch processing'
    )

    args = parser.parse_args()
    
    # Validate duration
    if args.duration <= 0:
        print("Error: Clip duration must be positive")
        sys.exit(1)
    
    # Create and run splitter
    splitter = VideoSplitter(
        input_dir=args.input,
        output_dir=args.output,
        clip_duration=args.duration,
        naming_pattern=args.naming,
        quality=args.quality,
        resolve_integration=args.resolve,
        project_name=args.project_name,
        scene_detection=args.scene_detection,
        min_scene_duration=args.min_scene_duration,
        batch_mode=args.batch,
        resume_batch=args.resume
    )
    
    splitter.split_all_videos()


if __name__ == "__main__":
    main()
