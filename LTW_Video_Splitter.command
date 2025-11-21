#!/bin/bash
# LTW Video Splitter Pro Launcher (macOS)
# Make this file executable: chmod +x LTW_Video_Splitter.command

cd "$(dirname "$0")"

echo "🎬 LTW Video Splitter Pro"
echo "=========================="

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment found"
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found"
    echo "Consider creating one: python3 -m venv venv"
fi

# Launch GUI
python3 launch_gui.py
