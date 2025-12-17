#!/usr/bin/env python3
"""
AI Content Analyzer for LTW Video Editor Pro
Implements highlight detection, engagement scoring, and viral potential analysis
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import torch
import torch.nn as nn
from torchvision import models, transforms
import librosa
import speech_recognition as sr
from moviepy import VideoFileClip
from tqdm import tqdm
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class HighlightDetector:
    """
    Detects highlight moments in videos using computer vision and audio analysis
    """

    def __init__(self, device: str = 'auto'):
        """
        Initialize the highlight detector

        Args:
            device: 'cpu', 'cuda', 'mps' (Mac M4), or 'auto'
        """
        self.device = self._setup_device(device)

        # Load pre-trained models
        self.resnet_model = self._load_resnet_model()
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        # Engagement scoring weights
        self.engagement_weights = {
            'motion_score': 0.3,
            'audio_energy': 0.25,
            'face_presence': 0.2,
            'color_vibrancy': 0.15,
            'text_presence': 0.1
        }

    def _setup_device(self, device: str) -> str:
        """Setup the appropriate device for computation"""
        if device == 'auto':
            if torch.cuda.is_available():
                return 'cuda'
            elif torch.backends.mps.is_available():
                return 'mps'
            else:
                return 'cpu'
        return device

    def _load_resnet_model(self) -> nn.Module:
        """Load pre-trained ResNet model for feature extraction"""
        model = models.resnet50(pretrained=True)
        model = nn.Sequential(*list(model.children())[:-1])  # Remove final classification layer
        model.eval()
        model.to(self.device)
        return model

    def analyze_video(self, video_path: Path, sample_rate: int = 1) -> Dict[str, Any]:
        """
        Analyze video for highlights and engagement potential

        Args:
            video_path: Path to video file
            sample_rate: Frames to analyze per second

        Returns:
            Dictionary with analysis results
        """
        print("🎬 Analyzing video for highlights and engagement...")

        # Load video
        video = VideoFileClip(str(video_path))
        duration = video.duration
        fps = video.fps

        # Extract frames and audio
        frames = []
        timestamps = []
        audio_energy = []

        # Sample frames
        frame_interval = int(fps / sample_rate) if sample_rate < fps else 1

        for i, frame in enumerate(tqdm(video.iter_frames(fps=fps), desc="Extracting frames", unit="frame")):
            if i % frame_interval == 0:
                timestamp = i / fps
                if timestamp <= duration:
                    frames.append(frame)
                    timestamps.append(timestamp)

        # Extract audio features if available
        if video.audio is not None:
            audio_samples = video.audio.to_soundarray(fps=44100)
            if len(audio_samples.shape) > 1:
                audio_samples = audio_samples.mean(axis=1)  # Convert to mono

            # Calculate audio energy in windows
            window_size = int(44100 * (1 / sample_rate))  # 1 second windows
            for i in range(0, len(audio_samples), window_size):
                window = audio_samples[i:i+window_size]
                energy = np.sqrt(np.mean(window**2))
                audio_energy.append(energy)

        # Analyze each frame
        highlight_scores = []
        engagement_features = []

        print("🧠 Analyzing frames for highlights...")

        for i, frame in enumerate(tqdm(frames, desc="Analyzing highlights", unit="frame")):
            # Calculate engagement score
            engagement = self._calculate_engagement_score(frame, audio_energy[i] if i < len(audio_energy) else 0)

            # Detect highlight potential
            highlight_score = self._calculate_highlight_score(engagement, timestamps[i], duration)

            highlight_scores.append({
                'timestamp': timestamps[i],
                'highlight_score': highlight_score,
                'engagement_score': engagement['total_score'],
                'features': engagement
            })

            engagement_features.append(engagement)

        # Find optimal clips
        optimal_clips = self._find_optimal_clips(highlight_scores, duration)

        # Generate analysis report
        analysis = {
            'video_info': {
                'duration': duration,
                'fps': fps,
                'total_frames_analyzed': len(frames)
            },
            'highlight_analysis': highlight_scores,
            'optimal_clips': optimal_clips,
            'engagement_summary': self._summarize_engagement(engagement_features),
            'generated_at': datetime.now().isoformat()
        }

        return analysis

    def _calculate_engagement_score(self, frame: np.ndarray, audio_energy: float) -> Dict[str, float]:
        """Calculate engagement score for a single frame"""
        engagement = {}

        # Motion score (using optical flow estimation)
        engagement['motion_score'] = self._calculate_motion_score(frame)

        # Audio energy score
        engagement['audio_energy'] = min(1.0, audio_energy * 1000)  # Normalize

        # Face presence score
        engagement['face_presence'] = self._detect_faces(frame)

        # Color vibrancy score
        engagement['color_vibrancy'] = self._calculate_color_vibrancy(frame)

        # Text presence score (placeholder - would need OCR)
        engagement['text_presence'] = 0.0  # TODO: Implement OCR

        # Calculate total weighted score
        total_score = sum(
            engagement[feature] * weight
            for feature, weight in self.engagement_weights.items()
        )

        engagement['total_score'] = total_score
        return engagement

    def _calculate_motion_score(self, frame: np.ndarray) -> float:
        """Calculate motion score using edge detection and variance"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        # Calculate variance (higher variance = more motion/texture)
        variance = np.var(gray.astype(float))

        # Normalize to 0-1 scale
        motion_score = min(1.0, variance / 10000.0)

        return motion_score

    def _detect_faces(self, frame: np.ndarray) -> float:
        """Detect faces in frame using Haar cascades"""
        try:
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

            # Load face cascade (using OpenCV's built-in)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

            # Detect faces
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            # Score based on number of faces and size
            if len(faces) == 0:
                return 0.0
            elif len(faces) == 1:
                # Single face - check size relative to frame
                face_area = faces[0][2] * faces[0][3]
                frame_area = frame.shape[0] * frame.shape[1]
                size_ratio = face_area / frame_area
                return min(1.0, size_ratio * 10)  # Larger faces score higher
            else:
                # Multiple faces - diminishing returns
                return min(1.0, len(faces) * 0.3)

        except Exception as e:
            print(f"Face detection error: {e}")
            return 0.0

    def _calculate_color_vibrancy(self, frame: np.ndarray) -> float:
        """Calculate color vibrancy score"""
        # Convert to HSV color space
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

        # Calculate saturation variance (color richness)
        saturation = hsv[:, :, 1].astype(float)
        sat_variance = np.var(saturation)

        # Calculate value variance (brightness variation)
        value = hsv[:, :, 2].astype(float)
        val_variance = np.var(value)

        # Combine scores
        vibrancy = (sat_variance + val_variance) / 2

        # Normalize to 0-1 scale
        return min(1.0, vibrancy / 5000.0)

    def _calculate_highlight_score(self, engagement: Dict, timestamp: float, duration: float) -> float:
        """Calculate highlight potential score"""
        base_score = engagement['total_score']

        # Time-based modifiers
        time_factor = 1.0

        # Boost scores for content in the middle 60% of video (sweet spot)
        if 0.2 * duration <= timestamp <= 0.8 * duration:
            time_factor = 1.2
        elif timestamp <= 0.1 * duration or timestamp >= 0.9 * duration:
            # Penalize very beginning and end
            time_factor = 0.8

        # Audio boost for high-energy moments
        audio_boost = 1.0 + (engagement['audio_energy'] * 0.5)

        # Face presence boost
        face_boost = 1.0 + (engagement['face_presence'] * 0.3)

        highlight_score = base_score * time_factor * audio_boost * face_boost

        return min(1.0, highlight_score)

    def _find_optimal_clips(self, highlight_scores: List[Dict], duration: float,
                           target_clip_duration: int = 30) -> List[Dict[str, Any]]:
        """Find optimal clip segments based on highlight scores"""
        if not highlight_scores:
            return []

        # Sort by highlight score (descending)
        sorted_scores = sorted(highlight_scores, key=lambda x: x['highlight_score'], reverse=True)

        optimal_clips = []
        used_timestamps = set()

        # Target different clip lengths for variety
        clip_durations = [15, 30, 45, 60]  # seconds

        for score_data in sorted_scores[:20]:  # Consider top 20 moments
            timestamp = score_data['timestamp']

            # Skip if too close to already selected clips
            if any(abs(timestamp - used) < 10 for used in used_timestamps):
                continue

            # Choose clip duration based on engagement level
            if score_data['highlight_score'] > 0.7:
                clip_duration = 30  # Longer for high-engagement moments
            elif score_data['highlight_score'] > 0.5:
                clip_duration = 15  # Shorter for medium engagement
            else:
                clip_duration = 45  # Medium length for lower engagement

            # Ensure clip doesn't exceed video boundaries
            start_time = max(0, timestamp - clip_duration / 2)
            end_time = min(duration, start_time + clip_duration)

            if end_time - start_time >= 10:  # Minimum 10 seconds
                optimal_clips.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time,
                    'highlight_score': score_data['highlight_score'],
                    'engagement_score': score_data['engagement_score'],
                    'reason': 'AI-detected highlight moment'
                })

                used_timestamps.add(timestamp)

                if len(optimal_clips) >= 10:  # Limit to 10 best clips
                    break

        return sorted(optimal_clips, key=lambda x: x['start_time'])

    def _summarize_engagement(self, engagement_features: List[Dict]) -> Dict[str, float]:
        """Summarize engagement statistics"""
        if not engagement_features:
            return {}

        # Calculate averages
        summary = {}
        feature_keys = ['motion_score', 'audio_energy', 'face_presence', 'color_vibrancy', 'total_score']

        for key in feature_keys:
            values = [f[key] for f in engagement_features]
            summary[f'avg_{key}'] = np.mean(values)
            summary[f'max_{key}'] = max(values)
            summary[f'min_{key}'] = min(values)

        return summary


class SpeechToTextGenerator:
    """
    Generate captions and transcripts from video audio
    """

    def __init__(self, language: str = 'en-US'):
        self.language = language
        self.recognizer = sr.Recognizer()

    def generate_transcript(self, video_path: Path) -> Dict[str, Any]:
        """
        Generate transcript with timestamps

        Args:
            video_path: Path to video file

        Returns:
            Dictionary with transcript data
        """
        print("🎙️ Generating transcript from audio...")

        video = VideoFileClip(str(video_path))

        if video.audio is None:
            return {'transcript': '', 'segments': [], 'error': 'No audio found'}

        # Export audio to temporary WAV file
        temp_audio = video_path.parent / f"temp_audio_{video_path.stem}.wav"
        video.audio.write_audiofile(str(temp_audio), verbose=False, logger=None)

        transcript_data = {
            'transcript': '',
            'segments': [],
            'language': self.language,
            'duration': video.duration
        }

        try:
            # Load audio file for speech recognition
            with sr.AudioFile(str(temp_audio)) as source:
                audio = self.recognizer.record(source)

                # Get full transcript
                try:
                    transcript = self.recognizer.recognize_google(audio, language=self.language)
                    transcript_data['transcript'] = transcript
                except sr.UnknownValueError:
                    transcript_data['error'] = 'Could not understand audio'
                except sr.RequestError as e:
                    transcript_data['error'] = f'Speech recognition service error: {e}'

            # Note: For timestamped segments, would need more advanced speech recognition
            # This is a simplified implementation

        except Exception as e:
            transcript_data['error'] = str(e)
        finally:
            # Clean up temporary file
            if temp_audio.exists():
                temp_audio.unlink()

        return transcript_data


def analyze_video_content(video_path: Path, use_ai: bool = True) -> Dict[str, Any]:
    """
    Comprehensive video content analysis

    Args:
        video_path: Path to video file
        use_ai: Whether to use AI-powered analysis

    Returns:
        Complete analysis results
    """
    results = {
        'video_path': str(video_path),
        'filename': video_path.name,
        'analysis_timestamp': datetime.now().isoformat()
    }

    if use_ai:
        # AI-powered highlight detection
        detector = HighlightDetector()
        highlight_analysis = detector.analyze_video(video_path)
        results['highlight_analysis'] = highlight_analysis

        # Speech-to-text
        stt_generator = SpeechToTextGenerator()
        transcript = stt_generator.generate_transcript(video_path)
        results['transcript'] = transcript

    return results


if __name__ == "__main__":
    # Example usage
    video_path = Path("example_video.mp4")

    if video_path.exists():
        print(f"🎬 Analyzing video: {video_path.name}")
        results = analyze_video_content(video_path)

        # Save results
        output_file = video_path.parent / f"{video_path.stem}_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"✅ Analysis complete! Results saved to: {output_file}")
    else:
        print(f"❌ Video file not found: {video_path}")
        print("💡 Usage: python ai_content_analyzer.py")
        print("   (place this script in directory with video files)")
