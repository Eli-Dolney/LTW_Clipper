import argparse
from pathlib import Path

from src.core.edit_suite.beats import detect_beats as _detect_beats


def detect_beats(audio_path, output_path=None):
    """Analyze audio and export beat timestamps (Resolve-compatible JSON)."""
    print(f"🎧 Analyzing beat structure: {audio_path}")
    out = Path(output_path) if output_path else Path(audio_path).with_suffix(".json")
    try:
        beat_map = _detect_beats(Path(audio_path), out)
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    print(f"   🎹 Tempo: {beat_map.tempo:.2f} BPM")
    print(f"✅ Found {beat_map.total_beats} beats.")
    print(f"📄 Saved beat map to: {out}")
    print("🚀 NEXT STEP: Use Edit Suite tab or 'LTW_Import_Beat_Edits.lua' in Resolve!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect beats in music for video sync")
    parser.add_argument('--file', required=True, help='Path to music file (mp3/wav)')
    args = parser.parse_args()
    
    detect_beats(args.file)

