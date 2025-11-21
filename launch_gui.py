#!/usr/bin/env python3
"""
Launcher for LTW Video Splitter Pro GUI
Cross-platform (macOS/Windows)
"""

import sys
import os
import subprocess
import platform

def check_requirements():
    """Check if required packages are installed"""
    try:
        import customtkinter
        import tkinterdnd2
        import cv2
        import moviepy
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Installing requirements...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install requirements automatically")
            print("Please run: pip install -r requirements.txt")
            return False

def main():
    """Launch the GUI application"""
    print("🎬 LTW Video Splitter Pro")
    print("=" * 30)

    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
    else:
        print("⚠️  Not running in virtual environment (consider using one)")

    # Check platform
    system = platform.system()
    if system == "Darwin":
        print("🍎 Running on macOS")
    elif system == "Windows":
        print("🪟 Running on Windows")
    else:
        print(f"🐧 Running on {system}")

    # Check requirements
    if not check_requirements():
        input("Press Enter to exit...")
        return

    # Import and run GUI
    try:
        from gui import VideoSplitterGUI
        print("🚀 Starting GUI...")
        app = VideoSplitterGUI()
        app.run()
    except Exception as e:
        print(f"❌ Failed to start GUI: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
