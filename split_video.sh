#!/bin/bash
# Simple video splitter script - drag and drop a video file to split it

# Activate virtual environment
source venv/bin/activate

# Check if a file was provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <video_file>"
    echo "Or drag and drop a video file onto this script"
    exit 1
fi

# Get the video file path
video_file="$1"

# Check if file exists
if [ ! -f "$video_file" ]; then
    echo "Error: File '$video_file' not found"
    exit 1
fi

# Get the directory containing the video
video_dir=$(dirname "$video_file")

echo "Splitting video: $(basename "$video_file")"
echo "Output will be saved to: ~/Desktop/clips"
echo ""

# Run the video splitter
python video_splitter.py -i "$video_dir" -o ~/Desktop/clips

echo ""
echo "Done! Check your Desktop/clips folder for the results."
