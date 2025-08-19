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
from typing import List, Optional
import re
from tqdm import tqdm
import subprocess


class VideoSplitter:
    def __init__(self, input_dir: str = ".", output_dir: str = None, clip_duration: int = 30, 
                 naming_pattern: str = "{name}_part_{num:03d}", quality: str = "medium"):
        """
        Initialize the VideoSplitter
        
        Args:
            input_dir: Directory containing videos to split
            output_dir: Directory to save the clips (default: Desktop/clips)
            clip_duration: Duration of each clip in seconds
            naming_pattern: Pattern for clip naming (use {name}, {num}, {duration})
            quality: Video quality ('low', 'medium', 'high', 'original')
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
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True)
        
        # Supported video formats
        self.supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm'}
        
        # Quality settings
        self.quality_settings = {
            'low': {'bitrate': '1000k', 'resolution': '640x360'},
            'medium': {'bitrate': '2000k', 'resolution': '1280x720'},
            'high': {'bitrate': '4000k', 'resolution': '1920x1080'},
            'original': {'bitrate': None, 'resolution': None}
        }
    
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
            print(f"  Creating {num_clips} clips of {self.clip_duration} seconds each")
            
            # Clean the base filename
            base_name = self.clean_filename(video_path.stem)
            
            # Create clips with progress bar
            clips_created = 0
            for i in tqdm(range(num_clips), desc=f"Creating clips", unit="clip"):
                try:
                    start_time = i * self.clip_duration
                    end_time = min((i + 1) * self.clip_duration, duration)
                    segment_duration = max(0.001, end_time - start_time)
                    
                    # Generate output filename using naming pattern
                    output_filename = self.naming_pattern.format(
                        name=base_name,
                        num=i+1,
                        duration=self.clip_duration
                    ) + ".mp4"
                    output_path = self.output_dir / output_filename
                    
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
                    
                except Exception as clip_error:
                    print(f"    ✗ Error creating clip {i+1}: {str(clip_error)}")
                    # Continue with next clip instead of stopping
                    continue
            
            # Clean up
            video.close()
            print(f"  ✓ Completed: {clips_created} clips created in {self.output_dir}")
            print()
            return clips_created
            
        except Exception as e:
            print(f"  ✗ Error processing {video_path.name}: {str(e)}\n")
            return 0
    
    def split_all_videos(self) -> int:
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
        
        print(f"🎉 All done! Created {total_clips} clips in '{self.output_dir}'")
        return total_clips


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
        choices=['low', 'medium', 'high', 'original'],
        default='medium',
        help='Video quality (default: medium)'
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
        quality=args.quality
    )
    
    splitter.split_all_videos()


if __name__ == "__main__":
    main()
