#!/usr/bin/env python3
"""Interactive installer for LTW Video Splitter Pro.

Creates a local ``venv`` and installs dependencies from ``requirements.txt``.
Kept separate from the packaging config in ``pyproject.toml``. Use this if
you just want the app running; use ``pip install -e .[dev]`` if you want an
installable package for development.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    print(f"🔧 {description}...")
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def main() -> None:
    print("🎬 LTW Video Splitter Pro - Setup")
    print("=" * 40)

    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ required. You have Python {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} detected")

    venv_path = Path("venv")
    if venv_path.exists():
        print("⚠️  Virtual environment already exists")
        recreate = input("Recreate virtual environment? (y/N): ").lower().strip()
        if recreate == "y":
            run_command("rm -rf venv", "Removing old virtual environment")
        else:
            print("✅ Using existing virtual environment")
            return

    if not run_command(f"{sys.executable} -m venv venv", "Creating virtual environment"):
        sys.exit(1)

    pip_cmd = "venv/bin/pip" if os.name != "nt" else "venv\\Scripts\\pip"
    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        sys.exit(1)
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Installing requirements"):
        sys.exit(1)

    if os.name != "nt":
        run_command("chmod +x LTW_Video_Splitter.command", "Making macOS launcher executable")
        run_command("chmod +x split_video.sh", "Making shell script executable")

    print("\n🎉 Setup complete!")
    print("\n🚀 Launch the application:")
    if os.name == "nt":
        print("   Double-click: LTW_Video_Splitter.bat")
    else:
        print("   Double-click: LTW_Video_Splitter.command")
    print("   Or manually: python launch_gui.py")
    print("\n📚 For help, see README.md")


if __name__ == "__main__":
    main()
