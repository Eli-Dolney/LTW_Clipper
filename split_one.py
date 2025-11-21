#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

# Ensure we can import from current project
sys.path.append('.')
from video_splitter import VideoSplitter


def main():
    parser = argparse.ArgumentParser(description="Split a single video file into clips")
    parser.add_argument('--file', required=True, help='Path to the video file to split')
    parser.add_argument('-d', '--duration', type=int, default=30, help='Clip duration in seconds (default: 30)')
    parser.add_argument('-n', '--naming', default='{project}_{name}_part_{num:03d}', help='Naming pattern for clips')
    parser.add_argument('-q', '--quality', choices=['youtube_sd', 'youtube_hd', 'youtube_4k', 'original'], default='youtube_hd', help='Output quality')
    parser.add_argument('--resolve', action='store_true', default=True, help='Generate Resolve project files')
    parser.add_argument('--project-name', default=None, help='Name for Resolve project')
    parser.add_argument('--scene-detection', action='store_true', help='Use intelligent scene detection')
    parser.add_argument('--min-scene-duration', type=int, default=10, help='Minimum scene duration')
    parser.add_argument('--batch', action='store_true', help='Process all videos in directory (batch mode)')
    parser.add_argument('--resume', action='store_true', help='Resume interrupted batch processing')

    args = parser.parse_args()

    video_path = Path(args.file)
    if not video_path.exists():
        print(f"Error: File not found: {video_path}")
        sys.exit(1)

    splitter = VideoSplitter(
        input_dir=str(video_path.parent),
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
    splitter.split_video(video_path)


if __name__ == '__main__':
    main()
