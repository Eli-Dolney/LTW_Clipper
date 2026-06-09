#!/bin/bash
# Simple video splitter script - drag and drop a video file to split it

set -e

# Change to script directory so relative paths work
cd "$(dirname "$0")"

# Activate virtual environment if present
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

if [ $# -eq 0 ]; then
    echo "Usage: $0 <video_file>"
    echo "Or drag and drop a video file onto this script"
    exit 1
fi

video_file="$1"

if [ ! -f "$video_file" ]; then
    echo "Error: File '$video_file' not found"
    exit 1
fi

video_dir=$(dirname "$video_file")

echo "Splitting video: $(basename "$video_file")"
echo "Output will be saved to: ~/Desktop/clips"
echo ""

# Run the video splitter as a module so src imports resolve
PYTHONPATH="$(pwd)" python -m src.core.video_splitter -i "$video_dir" -o ~/Desktop/clips

echo ""
echo "Done! Check your Desktop/clips folder for the results."
