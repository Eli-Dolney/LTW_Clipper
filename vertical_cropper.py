#!/usr/bin/env python3
"""
Vertical Video Cropper for Social Media (TikTok/Shorts/Reels)
Converts landscape (16:9) videos to portrait (9:16) with smart centering.
"""

import argparse
from pathlib import Path
from moviepy import VideoFileClip
import math

def crop_to_vertical(video_path, output_path=None):
    """
    Crops a video to 9:16 aspect ratio, keeping the center in focus.
    """
    video_path = Path(video_path)
    if output_path is None:
        output_path = video_path.parent / f"{video_path.stem}_vertical.mp4"
    
    print(f"📱 Converting to vertical: {video_path.name}")
    
    try:
        clip = VideoFileClip(str(video_path))
        
        # Target aspect ratio 9:16
        target_ratio = 9/16
        current_ratio = clip.w / clip.h
        
        if current_ratio > target_ratio:
            # Video is too wide (landscape), need to crop sides
            new_width = clip.h * target_ratio
            # Center crop
            x1 = (clip.w / 2) - (new_width / 2)
            x2 = (clip.w / 2) + (new_width / 2)
            
            cropped_clip = clip.cropped(x1=x1, y1=0, x2=x2, y2=clip.h)
        else:
            # Video is too tall (unlikely for standard video), or already vertical
            cropped_clip = clip
            
        # Resize to standard 1080x1920 if needed (optional, good for quality)
        # cropped_clip = cropped_clip.resize(height=1920)
        
        print("   ⚡ Rendering vertical clip...")
        cropped_clip.write_videofile(
            str(output_path),
            codec='libx264',
            audio_codec='aac'
        )
        
        print(f"   ✅ Saved to: {output_path.name}")
        clip.close()
        cropped_clip.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error converting {video_path.name}: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert videos to vertical 9:16 format")
    parser.add_argument('--file', help='Specific video file to convert')
    parser.add_argument('--dir', help='Directory of videos to convert')
    
    args = parser.parse_args()
    
    if args.file:
        crop_to_vertical(args.file)
    elif args.dir:
        folder = Path(args.dir)
        videos = list(folder.glob("*.mp4"))
        print(f"Found {len(videos)} videos in {folder}")
        for vid in videos:
            if "_vertical" not in vid.name: # Avoid re-processing
                crop_to_vertical(vid)
    else:
        print("Please provide --file or --dir")

