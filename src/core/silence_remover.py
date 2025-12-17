# 🎙️ Silence Remover / Jump Cut Generator
# Finds silence in a video and generates an EDL (Edit Decision List)
# for DaVinci Resolve to automatically cut out the boring parts.

import argparse
import os
from moviepy import VideoFileClip
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

def generate_edl(video_path, output_edl):
    """
    Generates a CMX 3600 EDL file based on non-silent parts of the video.
    """
    print(f"🎧 Analyzing audio for: {video_path}")
    
    # Extract audio
    video = VideoFileClip(video_path)
    audio_path = "temp_audio.wav"
    video.audio.write_audiofile(audio_path, logger=None)
    
    # Load into pydub
    audio = AudioSegment.from_wav(audio_path)
    
    # Detect non-silent chunks
    # min_silence_len: ms (500ms = 0.5s)
    # silence_thresh: dBFS (anything quieter than -40dB is silence)
    print("   🔍 Detecting speech...")
    chunks = detect_nonsilent(audio, min_silence_len=500, silence_thresh=-40, seek_step=100)
    
    # Create EDL content
    edl_content = f"TITLE: {os.path.basename(video_path)}\nFCM: NON-DROP FRAME\n"
    
    # Convert ms to frames (assuming 30fps for simplicity, ideally read from video)
    fps = video.fps
    
    def ms_to_tc(ms):
        total_seconds = ms / 1000
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        frames = int((total_seconds - int(total_seconds)) * fps)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

    # Create timeline segments
    timeline_start_ms = 0
    
    print(f"   ✂️ Found {len(chunks)} active segments. Generating EDL...")
    
    for i, (start_ms, end_ms) in enumerate(chunks):
        # Add a little buffer (padding)
        start_ms = max(0, start_ms - 200)
        end_ms = min(len(audio), end_ms + 200)
        
        duration_ms = end_ms - start_ms
        
        # Source In/Out
        src_in = ms_to_tc(start_ms)
        src_out = ms_to_tc(end_ms)
        
        # Record In/Out (Timeline position)
        dst_in = ms_to_tc(timeline_start_ms)
        dst_out = ms_to_tc(timeline_start_ms + duration_ms)
        
        # EDL Line
        # 001  AX       V     C        00:00:00:00 00:00:05:00 00:00:00:00 00:00:05:00
        line = f"{i+1:03d}  AX       V     C        {src_in} {src_out} {dst_in} {dst_out}\n"
        edl_content += line
        
        # Update timeline position
        timeline_start_ms += duration_ms

    # Write EDL
    with open(output_edl, "w") as f:
        f.write(edl_content)
        
    # Cleanup
    os.remove(audio_path)
    video.close()
    
    print(f"✅ EDL Saved: {output_edl}")
    print("🚀 IMPORT INSTRUCTION:")
    print("   1. Open Resolve")
    print("   2. File -> Import -> Timeline...")
    print("   3. Select this .edl file")
    print("   4. Point to the original video file when asked")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate EDL to remove silence from video")
    parser.add_argument('--file', required=True, help='Video file to process')
    args = parser.parse_args()
    
    output = os.path.splitext(args.file)[0] + "_CUT.edl"
    generate_edl(args.file, output)

