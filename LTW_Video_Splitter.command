#!/bin/bash
# LTW Video Editor Pro - macOS Launcher
# Double-click this file to launch the application

cd "$(dirname "$0")"

echo "🎬 LTW Video Editor Pro"
echo "========================"

# Check for venv
if [ -d "venv" ]; then
    echo "✅ Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found"
    echo "💡 Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
fi

# Launch the app
echo "🚀 Launching application..."
python3 launch_gui.py

# Keep terminal open on error
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Application exited with error"
    echo "Press any key to close..."
    read -n 1
fi
