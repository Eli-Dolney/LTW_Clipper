#!/usr/bin/env python3
"""
LTW Video Editor Pro - GUI Launcher
Launches the professional video editing interface
"""

import sys
import os
from pathlib import Path

# Ensure we're in the right directory
os.chdir(Path(__file__).parent)

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    
    try:
        import customtkinter
    except ImportError:
        missing.append("customtkinter")
        
    try:
        import tkinterdnd2
    except ImportError:
        print("⚠️  tkinterdnd2 not installed - drag & drop will be disabled")
        
    try:
        from moviepy import VideoFileClip
    except ImportError:
        missing.append("moviepy")
        
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")
        
    try:
        from tqdm import tqdm
    except ImportError:
        missing.append("tqdm")
        
    if missing:
        print("❌ Missing dependencies:")
        for dep in missing:
            print(f"   - {dep}")
        print("\n💡 Install with: pip install " + " ".join(missing))
        return False
        
    return True

def main():
    """Main entry point"""
    print("🎬 LTW Video Editor Pro v2.0")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        sys.exit(1)
        
    print("✅ All dependencies OK")
    print("🚀 Launching GUI...")
    print()
    
    try:
        # Import and run the new GUI
        from gui.main_app import LTWVideoEditorPro
        
        app = LTWVideoEditorPro()
        app.run()
        
    except Exception as e:
        print(f"❌ Failed to launch GUI: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to old GUI
        print("\n⚠️  Attempting to launch legacy GUI...")
        try:
            from gui import VideoSplitterGUI
            app = VideoSplitterGUI()
            app.run()
        except Exception as e2:
            print(f"❌ Legacy GUI also failed: {e2}")
            sys.exit(1)

if __name__ == "__main__":
    main()
