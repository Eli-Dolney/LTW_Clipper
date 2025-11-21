@echo off
REM LTW Video Splitter Pro Launcher (Windows)
REM Double-click this file to run the GUI

cd /d "%~dp0"

echo 🎬 LTW Video Splitter Pro
echo ==========================

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo ✅ Virtual environment found
    call venv\Scripts\activate.bat
) else (
    echo ⚠️  No virtual environment found
    echo Consider creating one: python -m venv venv
)

REM Launch GUI
python launch_gui.py

pause
