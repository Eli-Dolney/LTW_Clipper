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
    parser.add_argument('-n', '--naming', default='{name}_part_{num:03d}', help='Naming pattern for clips')
    parser.add_argument('-q', '--quality', choices=['low', 'medium', 'high', 'original'], default='medium', help='Output quality')

    args = parser.parse_args()

    video_path = Path(args.file)
    if not video_path.exists():
        print(f"Error: File not found: {video_path}")
        sys.exit(1)

    splitter = VideoSplitter(input_dir=str(video_path.parent), output_dir=None, clip_duration=args.duration, naming_pattern=args.naming, quality=args.quality)
    splitter.split_video(video_path)


if __name__ == '__main__':
    main()
