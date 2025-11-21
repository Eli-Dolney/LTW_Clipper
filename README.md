# LTW Professional Video Splitter

A professional-grade Python tool for YouTube content creators that splits videos into clips with DaVinci Resolve integration. Features automatic organization, metadata tracking, and Resolve project generation for streamlined video editing workflows.

## Features

### Core Functionality
- Split videos into clips of specified duration (default: 30 seconds)
- Support for multiple video formats (MP4, AVI, MOV, MKV, FLV, WMV, WEBM)
- Batch processing of multiple videos with progress tracking
- Reliable audio encoding (AAC 160k @ 44.1kHz with retry mechanism)

### Professional Features
- **DaVinci Resolve Integration**: Automatic project file generation and Lua scripts for easy import
- **Professional Organization**: Clips, metadata, and project files in structured directories
- **YouTube-Optimized Quality**: SD (480p), HD (1080p), and 4K (2160p) presets
- **Metadata Tracking**: JSON files with complete clip information and timestamps
- **Custom Naming Patterns**: Flexible naming with project names, timestamps, and numbering
- **Intelligent Scene Detection**: Automatically split videos at natural scene boundaries using computer vision
- **Batch Processing with Resume**: Process multiple videos with automatic progress saving and resume capability

### Performance & Compatibility
- GPU acceleration support (NVIDIA RTX series on Windows)
- Optimized for Apple Silicon (M1/M2/M3/M4) on macOS
- Hardware-accelerated encoding with FFmpeg
- Resume-capable processing with error recovery

## System Requirements

### macOS (Apple Silicon M1/M2/M3/M4)
- macOS 12.0 or later
- Python 3.9 or later
- FFmpeg (recommended for better performance)

### Windows 11 (NVIDIA RTX 4080)
- Windows 11
- Python 3.9 or later
- NVIDIA GPU drivers (for hardware acceleration)
- FFmpeg (recommended for better performance)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Eli-Dolney/LTW_Clipper.git
cd LTW_Clipper
```

### 2. Quick Setup (Recommended)

```bash
# Run the automated setup script (does everything automatically)
python3 setup.py
```

This will:
- ✅ Create a virtual environment
- ✅ Install all required dependencies
- ✅ Make launcher scripts executable
- ✅ Set up everything for you

### 3. Manual Setup (Alternative)

**Option A: Using Virtual Environment**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Option B: Global Installation**
```bash
pip install -r requirements.txt
```

### 3. Install FFmpeg (Recommended)

**macOS:**
```bash
# Using Homebrew
brew install ffmpeg

# Or using MacPorts
sudo port install ffmpeg
```

**Windows:**
1. Download from [FFmpeg website](https://ffmpeg.org/download.html)
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add to PATH environment variable
4. Restart your terminal/command prompt

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

## 🎨 GUI Mode (Recommended)

### Professional Desktop Application

**LTW Video Splitter Pro** includes a beautiful, modern GUI that works on both macOS and Windows.

#### Quick Launch:
- **macOS**: Double-click `LTW_Video_Splitter.command`
- **Windows**: Double-click `LTW_Video_Splitter.bat`
- **Manual**: `python launch_gui.py`

#### Features:
- 🎯 **Drag & Drop** - Drop video files directly onto the interface
- 📊 **Real-time Progress** - Visual progress bars and status updates
- ⚙️ **Professional Settings** - All options in an intuitive interface
- 👀 **Clip Preview** - See exactly what clips will be created before processing
- 📦 **Batch Processing** - Process entire directories with resume capability
- 🎬 **Scene Detection** - AI-powered intelligent splitting

#### GUI Features:
- 🎬 **Drag & Drop Interface** - Drop video files or folders directly
- 📊 **Live Progress Tracking** - Real-time progress bars and file status
- ⚙️ **Professional Controls** - Quality presets, duration settings, naming patterns
- 🎭 **DaVinci Resolve Integration** - Automatic project file generation
- 🧠 **AI Scene Detection** - Intelligent splitting at natural scene boundaries
- 📦 **Batch Mode** - Process entire directories with resume capability
- 👀 **Clip Preview** - Preview exactly what clips will be created
- 🌓 **Dark Mode** - Modern dark theme optimized for video editing

#### Cross-Platform:
- ✅ **macOS** (Intel/Apple Silicon) - Native performance
- ✅ **Windows** (NVIDIA/AMD) - GPU acceleration support
- ✅ **Offline** - No internet required, all processing local

---

## 💻 Command Line Usage

### Basic Usage

Split all videos in the current directory into 30-second clips (saves to Desktop/clips):
```bash
python video_splitter.py
```

### Quick Split (Drag & Drop)

1. **Make the script executable** (macOS/Linux only):
   ```bash
   chmod +x split_video.sh
   ```

2. **Drag and drop a video file** onto the `split_video.sh` script, or run:
   ```bash
   ./split_video.sh /path/to/your/video.mp4
   ```

### Advanced Usage

**Specify input directory:**
```bash
python video_splitter.py -i /path/to/videos
```

**Specify output directory:**
```bash
python video_splitter.py -o /path/to/clips
```

**Change clip duration:**
```bash
python video_splitter.py -d 60  # 60-second clips
```

**Combine all options:**
```bash
python video_splitter.py -i videos -o clips -d 45
```

### Batch Processing with Resume

Process all videos in a directory with automatic resume capability:

```bash
# Process all videos in a directory
python video_splitter.py --batch --input "/path/to/videos"

# With scene detection for intelligent splitting
python video_splitter.py --batch --scene-detection --input "/path/to/videos"

# Resume interrupted batch processing
python video_splitter.py --batch --resume --input "/path/to/videos"

# Batch with custom settings
python video_splitter.py --batch --input "/path/to/videos" --duration 45 --quality youtube_hd --project-name "My_Batch_Project"
```

**Batch Processing Features:**
- ✅ Processes multiple videos automatically
- ✅ Saves progress and allows resume after interruption
- ✅ Creates organized project structure
- ✅ Generates DaVinci Resolve projects for all videos
- ✅ Press Ctrl+C to interrupt safely (progress is saved)

### Single File Processing

For processing just one video file:

```bash
# Activate virtual environment (if using one)
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Process single file
python split_one.py --file "/full/path/to/video.mp4" -d 45 -q medium
```

**Examples:**
```bash
# Basic usage
python split_one.py --file "My Video.mp4" -d 45

# With special characters (use single quotes)
python split_one.py --file 'you need to learn Python RIGHT NOW!! ⧸⧸ EP 1 [mRMmlo_Uqcs].mp4' -d 45

# With quality settings
python split_one.py --file "video.mp4" -d 30 -q high -n "{name}_part_{num:03d}"

# Intelligent scene detection
python split_one.py --file "video.mp4" --scene-detection --min-scene-duration 15
```

### Command Line Options

**video_splitter.py:**
- `-i, --input`: Input directory containing videos (default: current directory)
- `-o, --output`: Output directory for clips (default: Desktop/clips)
- `-d, --duration`: Duration of each clip in seconds (default: 30)

**split_one.py:**
- `--file`: Path to the video file to split
- `-d, --duration`: Duration of each clip in seconds (default: 30)
- `-q, --quality`: Video quality ('youtube_sd', 'youtube_hd', 'youtube_4k', 'original', default: youtube_hd)
- `-n, --naming`: Naming pattern (supports {project}, {name}, {num}, {duration}, {timestamp})
- `--resolve`: Generate DaVinci Resolve project files (default: enabled)
- `--project-name`: Custom name for Resolve project (auto-generated if not specified)
- `--scene-detection`: Use intelligent scene detection for natural splitting
- `--min-scene-duration`: Minimum duration for detected scenes (default: 10 seconds)
- `--batch`: Process all videos in input directory (batch mode)
- `--resume`: Resume interrupted batch processing

## Performance Optimization

### For NVIDIA RTX 4080 (Windows)
- The script automatically detects NVIDIA GPUs
- Hardware acceleration is enabled by default
- For best performance, ensure latest NVIDIA drivers are installed

### For Apple Silicon (M1/M2/M3/M4)
- Optimized for Apple's Metal framework
- Automatic hardware acceleration
- No additional configuration needed

## Example Output

```
Found 2 video file(s) to process:
  - video1.mp4
  - video2.mp4

Processing: video1.mp4
  Duration: 120.50 seconds
  Creating 4 clips of 30 seconds each
    Created: video1_clip_001.mp4
    Created: video1_clip_002.mp4
    Created: video1_clip_003.mp4
    Created: video1_clip_004.mp4
  ✓ Completed: 4 clips created

Processing: video2.mp4
  Duration: 90.25 seconds
  Creating 3 clips of 30 seconds each
    Created: video2_clip_001.mp4
    Created: video2_clip_002.mp4
    Created: video2_clip_003.mp4
  ✓ Completed: 3 clips created

🎉 All done! Created 7 clips in 'clips'
```

## 🎯 Advanced Features

### Intelligent Scene Detection
Automatically detect scene changes and split videos at natural boundaries instead of fixed time intervals:
```bash
# Use scene detection for intelligent splitting
python split_one.py --file "video.mp4" --scene-detection --min-scene-duration 15
```

### Batch Processing with Resume
Process entire directories of videos with automatic progress saving:
```bash
# Process all videos in a directory
python video_splitter.py --batch --input "/path/to/videos"

# Resume after interruption
python video_splitter.py --batch --resume --input "/path/to/videos"
```

### Professional Project Organization
- Automatic project folder creation
- DaVinci Resolve project files
- Metadata JSON files for each clip
- Organized clip naming with timestamps

## Supported Video Formats

- MP4 (.mp4)
- AVI (.avi)
- MOV (.mov)
- MKV (.mkv)
- FLV (.flv)
- WMV (.wmv)
- WEBM (.webm)

## Quality Settings (YouTube Optimized)

- **youtube_sd**: 854x480, 2000k bitrate (YouTube SD/480p)
- **youtube_hd**: 1920x1080, 5000k bitrate (YouTube HD/1080p) - *Default*
- **youtube_4k**: 3840x2160, 15000k bitrate (YouTube 4K/2160p)
- **original**: Maintains original video quality

## Professional Output Structure

When you run the splitter, it creates a professional project structure:

```
Your_Project_Name/
├── clips/                    # All video clips (MP4)
├── metadata/                 # JSON metadata files
│   └── project_metadata.json # Detailed clip information
└── resolve_project/          # DaVinci Resolve integration
    ├── project.drp           # Resolve project file
    ├── project_import.lua    # Batch import script
    └── README.md             # Instructions for Resolve users
```

## Technical Details

- **Audio Encoding**: AAC 160k @ 44.1kHz with automatic retry on failure
- **Video Codec**: H.264 with fast preset for optimal quality/speed balance
- **Container**: MP4 with proper metadata
- **Error Recovery**: Continues processing even if individual clips fail
- **Progress Tracking**: Real-time progress bars with ETA
- **Resolve Integration**: XML project files and Lua automation scripts

## Troubleshooting

### Common Issues

**"No module named 'moviepy'" error:**
```bash
pip install -r requirements.txt
```

**FFmpeg not found:**
- Install FFmpeg (see installation section above)
- Make sure FFmpeg is in your system PATH

**Videos not being found:**
- Check that your video files have the supported extensions
- Verify the input directory path is correct
- Make sure the video files are not corrupted

**Permission denied on macOS/Linux:**
```bash
chmod +x split_video.sh
```

**Virtual environment not activating:**
```bash
# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

### Performance Issues

**Slow processing on Windows:**
- Update NVIDIA drivers
- Ensure GPU acceleration is enabled
- Close other GPU-intensive applications

**Slow processing on macOS:**
- Ensure you're using the latest macOS version
- Close other CPU-intensive applications
- Consider using lower quality settings for faster processing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Support

If you encounter any issues or have questions:
1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create a new issue with detailed information about your problem

---

**Note:** This tool is designed for personal use and educational purposes. Please respect copyright laws and only process videos you have the right to modify.
