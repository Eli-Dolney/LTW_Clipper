import librosa
import numpy as np
import argparse
import json
from pathlib import Path

def detect_beats(audio_path, output_path=None):
    """
    Analyzes audio file and detects beat timestamps.
    Exports to a JSON file compatible with our Resolve script.
    """
    print(f"🎧 Analyzing beat structure: {audio_path}")
    
    # Load audio
    try:
        y, sr = librosa.load(audio_path)
    except Exception as e:
        print(f"❌ Error loading audio: {e}")
        print("   (Make sure ffmpeg is installed: brew install ffmpeg)")
        return

    # Detect tempo and beats
    print("   📊 Calculating tempo...")
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    print(f"   🎹 Tempo: {tempo:.2f} BPM")
    
    # Convert frames to time
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    
    # Create beat list
    beats = []
    for t in beat_times:
        beats.append(float(t))
        
    # Save to JSON
    if output_path is None:
        output_path = Path(audio_path).with_suffix('.json')
        
    data = {
        "source": str(audio_path),
        "tempo": float(tempo),
        "total_beats": len(beats),
        "beats": beats
    }
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
        
    print(f"✅ Found {len(beats)} beats.")
    print(f"📄 Saved beat map to: {output_path}")
    print("🚀 NEXT STEP: Run 'LTW_Import_Beat_Edits.lua' in Resolve to auto-cut clips to these beats!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect beats in music for video sync")
    parser.add_argument('--file', required=True, help='Path to music file (mp3/wav)')
    args = parser.parse_args()
    
    detect_beats(args.file)

