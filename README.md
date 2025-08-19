# LTW Video Splitter

A Python script that splits downloaded videos into customizable clips (default: 30 seconds). Optimized for macOS and Windows with GPU acceleration support.

## Features

- Split videos into clips of specified duration (default: 30 seconds)
- Support for multiple video formats (MP4, AVI, MOV, MKV, FLV, WMV, WEBM)
- Batch processing of multiple videos
- Customizable input and output directories
- Progress tracking and detailed output
- Reliable audio in all clips (AAC 160k @ 44.1kHz, with retry)
- GPU acceleration support (NVIDIA RTX series on Windows)
- Optimized for Apple Silicon (M1/M2/M3/M4) on macOS

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

### 2. Set Up Python Environment

**Option A: Using Virtual Environment (Recommended)**
```bash
# Create virtual environment
python -m venv venv

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

## Usage

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
```

### Command Line Options

**video_splitter.py:**
- `-i, --input`: Input directory containing videos (default: current directory)
- `-o, --output`: Output directory for clips (default: Desktop/clips)
- `-d, --duration`: Duration of each clip in seconds (default: 30)

**split_one.py:**
- `--file`: Path to the video file to split
- `-d, --duration`: Duration of each clip in seconds (default: 30)
- `-q, --quality`: Video quality ('low', 'medium', 'high', 'original', default: medium)
- `-n, --naming`: Naming pattern (supports {name}, {num}, {duration})

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

## Supported Video Formats

- MP4 (.mp4)
- AVI (.avi)
- MOV (.mov)
- MKV (.mkv)
- FLV (.flv)
- WMV (.wmv)
- WEBM (.webm)

## Quality Settings

- **Low**: 640x360, 1000k bitrate
- **Medium**: 1280x720, 2000k bitrate (default)
- **High**: 1920x1080, 4000k bitrate
- **Original**: Maintains original video quality

## Notes

- The script automatically creates the output directory if it doesn't exist
- Clips are saved in MP4 format with H.264 video codec and AAC audio codec
- All clips keep audio; the script uses ffmpeg with a safe audio encode and retry
- The last clip of each video may be shorter than the specified duration if the video length isn't evenly divisible
- Processing time depends on video length and your computer's performance
- GPU acceleration is automatically detected and used when available

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
