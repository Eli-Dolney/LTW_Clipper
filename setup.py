#!/usr/bin/env python3
"""
Setup script for LTW Video Splitter Pro
"""

import sys
import subprocess
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main setup function"""
    print("🎬 LTW Video Splitter Pro - Setup")
    print("=" * 40)

    # Check Python version
    if sys.version_info < (3, 9):
        print(f"❌ Python 3.9+ required. You have Python {sys.version}")
        sys.exit(1)

    print(f"✅ Python {sys.version.split()[0]} detected")

    # Check if virtual environment exists
    venv_path = Path("venv")
    if venv_path.exists():
        print("⚠️  Virtual environment already exists")
        recreate = input("Recreate virtual environment? (y/N): ").lower().strip()
        if recreate == 'y':
            run_command("rm -rf venv", "Removing old virtual environment")
        else:
            print("✅ Using existing virtual environment")
            return

    # Create virtual environment
    if not run_command("python3 -m venv venv", "Creating virtual environment"):
        sys.exit(1)

    # Activate virtual environment and install requirements
    pip_cmd = "venv/bin/pip" if os.name != 'nt' else "venv\\Scripts\\pip"

    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        sys.exit(1)

    if not run_command(f"{pip_cmd} install -r requirements.txt", "Installing requirements"):
        sys.exit(1)

    # Make launch scripts executable on Unix-like systems
    if os.name != 'nt':
        run_command("chmod +x LTW_Video_Splitter.command", "Making macOS launcher executable")
        run_command("chmod +x split_video.sh", "Making shell script executable")

    print("\n🎉 Setup complete!")
    print("\n🚀 Launch the application:")
    if os.name == 'nt':
        print("   Double-click: LTW_Video_Splitter.bat")
    else:
        print("   Double-click: LTW_Video_Splitter.command")
    print("   Or manually: python launch_gui.py")

    print("\n📚 For help, see README.md")

if __name__ == "__main__":
    main()
