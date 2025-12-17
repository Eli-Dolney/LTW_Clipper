#!/usr/bin/env python3
"""
LTW Smart Clip Finder (Opus Clip-Style)
Uses transcripts to find the most engaging moments in your video.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple

# Engagement keywords (words that indicate high-value content)
ENGAGEMENT_KEYWORDS = {
    'high': ['amazing', 'incredible', 'watch this', 'here\'s how', 'secret', 'trick', 'hack', 
             'you need to', 'game changer', 'mind blowing', 'insane', 'epic', 'legendary'],
    'medium': ['important', 'key', 'remember', 'note', 'tip', 'pro tip', 'best', 'top',
               'essential', 'crucial', 'must know', 'should know'],
    'question': ['how', 'what', 'why', 'when', 'where', 'can you', 'do you', 'have you'],
    'action': ['let\'s', 'we\'re going', 'now we', 'next', 'step', 'first', 'then', 'finally']
}

def score_segment(text: str, start_time: float, end_time: float) -> float:
    """
    Scores a transcript segment based on engagement keywords.
    Returns a score from 0-1.
    """
    text_lower = text.lower()
    score = 0.0
    
    # High-value keywords
    for keyword in ENGAGEMENT_KEYWORDS['high']:
        if keyword in text_lower:
            score += 0.3
    
    # Medium-value keywords
    for keyword in ENGAGEMENT_KEYWORDS['medium']:
        if keyword in text_lower:
            score += 0.15
    
    # Questions (engagement hooks)
    for keyword in ENGAGEMENT_KEYWORDS['question']:
        if keyword in text_lower:
            score += 0.2
    
    # Action words (momentum)
    for keyword in ENGAGEMENT_KEYWORDS['action']:
        if keyword in text_lower:
            score += 0.1
    
    # Length bonus (not too short, not too long)
    duration = end_time - start_time
    if 5 <= duration <= 30:
        score += 0.2
    elif duration > 60:
        score -= 0.1  # Too long
    
    # Cap at 1.0
    return min(1.0, score)

def find_best_clips(transcript_path: Path, top_n: int = 10) -> List[Dict]:
    """
    Analyzes transcript and returns the top N most engaging segments.
    """
    print(f"📊 Analyzing transcript: {transcript_path.name}")
    
    # Load transcript
    with open(transcript_path, 'r', encoding='utf-8') as f:
        if transcript_path.suffix == '.json':
            data = json.load(f)
            segments = data.get('segments', [])
        else:
            # Assume SRT format (simplified parsing)
            segments = []
            content = f.read()
            # Parse SRT (simplified)
            pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.+?)(?=\n\d+\n|\Z)'
            for match in re.finditer(pattern, content, re.DOTALL):
                num, start_tc, end_tc, text = match.groups()
                # Convert timecode to seconds
                def tc_to_sec(tc):
                    h, m, s = tc.split(':')
                    s, ms = s.split(',')
                    return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000
                
                segments.append({
                    'start': tc_to_sec(start_tc),
                    'end': tc_to_sec(end_tc),
                    'text': text.strip()
                })
    
    # Score each segment
    scored_segments = []
    for seg in segments:
        score = score_segment(seg['text'], seg['start'], seg['end'])
        scored_segments.append({
            'start': seg['start'],
            'end': seg['end'],
            'text': seg['text'],
            'score': score,
            'duration': seg['end'] - seg['start']
        })
    
    # Sort by score (highest first)
    scored_segments.sort(key=lambda x: x['score'], reverse=True)
    
    # Return top N
    top_clips = scored_segments[:top_n]
    
    print(f"✅ Found {len(top_clips)} high-engagement moments:")
    for i, clip in enumerate(top_clips, 1):
        print(f"   {i}. [{clip['start']:.1f}s - {clip['end']:.1f}s] Score: {clip['score']:.2f}")
        print(f"      \"{clip['text'][:60]}...\"")
    
    return top_clips

def export_clip_list(clips: List[Dict], output_path: Path):
    """
    Exports clip list to JSON for Resolve import.
    """
    data = {
        'total_clips': len(clips),
        'clips': clips,
        'format': 'LTW_Smart_Clips'
    }
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n📄 Exported to: {output_path}")
    print("🚀 Import into Resolve using: LTW_Import_Smart_Clips.lua")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Find best clips using transcript analysis")
    parser.add_argument('--transcript', required=True, help='Path to transcript file (SRT/JSON)')
    parser.add_argument('--top', type=int, default=10, help='Number of top clips to find')
    parser.add_argument('--output', help='Output JSON file (default: transcript_smart_clips.json)')
    
    args = parser.parse_args()
    
    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"❌ File not found: {transcript_path}")
        exit(1)
    
    clips = find_best_clips(transcript_path, args.top)
    
    output_path = Path(args.output) if args.output else transcript_path.parent / f"{transcript_path.stem}_smart_clips.json"
    export_clip_list(clips, output_path)

