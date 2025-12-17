# 🎬 LTW Video Splitter Pro

**Professional video splitting tool with GUI, AI features, and DaVinci Resolve integration.**

Split long videos into clips automatically. Perfect for creating YouTube Shorts, TikTok videos, and Instagram Reels from your long-form content.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)

## ✨ Features

- **🖥️ Professional GUI** - Modern dark-themed interface with sidebar navigation
- **✂️ Smart Splitting** - Time-based or AI scene detection
- **🎯 Quality Presets** - YouTube SD/HD/4K optimized outputs
- **🎭 DaVinci Resolve Integration** - Auto-generate import scripts
- **📦 Batch Processing** - Process multiple videos with resume capability
- **💾 Preset System** - Save and reuse your favorite settings
- **🔧 Command Line** - Full CLI support for automation

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Eli-Dolney/LTW_Clipper.git
cd LTW_Clipper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Launch GUI

```bash
python launch_gui.py
```

Or double-click:
- **macOS**: `LTW_Video_Splitter.command`
- **Windows**: `LTW_Video_Splitter.bat`

### Command Line Usage

```bash
# Split all videos in current directory
python video_splitter.py

# Split a single video
python split_one.py --file "video.mp4" -d 30 -q youtube_hd

# With scene detection
python split_one.py --file "video.mp4" --scene-detection

# Batch process a folder
python video_splitter.py --batch --input "/path/to/videos"
```

## 📋 Options

| Option | Description | Default |
|--------|-------------|---------|
| `-d, --duration` | Clip duration (seconds) | 30 |
| `-q, --quality` | Quality preset | youtube_hd |
| `--scene-detection` | AI scene boundary splitting | Off |
| `--batch` | Process all videos in folder | Off |
| `--resume` | Resume interrupted batch | Off |
| `--project-name` | Custom project name | Auto |

### Quality Presets

- `youtube_sd` - 480p, 2Mbps
- `youtube_hd` - 1080p, 5Mbps (default)
- `youtube_4k` - 4K, 15Mbps
- `original` - Keep source quality

## 🎨 GUI Features

The GUI includes 4 main tabs:

1. **Video Splitter** - Drag & drop files, adjust settings, process
2. **Opus Clip AI** - Multi-platform optimization (TikTok, Instagram, YouTube)
3. **DaVinci Resolve** - Script management and LUT gallery
4. **Settings** - Presets and configuration

### Built-in Presets

- Sports Montage (15s, 4K, scene detection)
- Tutorial Clips (45s, HD)
- Highlight Reel (30s, AI highlights)
- Quick TikTok (15s, vertical)
- Gaming Clips (20s, 4K)
- Cinematic (60s, film-style)

## 🎭 DaVinci Resolve Integration

Includes 11 automation scripts for Resolve:

- `LTW_Universal_Import.lua` - Import clips with timeline
- `LTW_Add_Transitions.lua` - Batch add transitions
- `LTW_Apply_Look.lua` - Apply color presets
- `LTW_Quick_Render.lua` - One-click render
- And more...

Install scripts: Go to **Resolve Tab** → **Install All Scripts**

## 📁 Project Structure

```
LTW_Clipper/
├── src/
│   ├── core/           # Core video processing modules
│   ├── gui/            # Professional GUI application
│   └── scripts/        # Helper scripts
├── resolve_scripts/     # DaVinci Resolve automation
├── presets/            # Processing presets
├── assets/             # LUTs and branding assets
├── launch_gui.py       # GUI launcher
├── requirements.txt    # Dependencies
└── README.md           # This file
```

## 📁 Output Structure

```
clips/
├── clips/              # Video clips
├── metadata/           # JSON metadata
└── resolve_project/    # Lua import scripts
```

## 🔧 Requirements

- Python 3.9+
- FFmpeg (recommended)
- 8GB RAM minimum

### macOS Note

If you get grey/blank windows, install Homebrew Python with Tk:

```bash
brew install python-tk@3.12
```

Then recreate the venv with `/opt/homebrew/bin/python3.12`.

## 📄 License

MIT License - See [LICENSE](LICENSE)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Made with ❤️ for content creators**
