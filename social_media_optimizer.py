#!/usr/bin/env python3
"""
Social Media Optimizer for LTW Video Editor Pro
Handles platform-specific formatting, aspect ratios, and viral optimization
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import json
from enum import Enum
from dataclasses import dataclass
import cv2
import numpy as np
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.video.fx import crop, resize


class Platform(Enum):
    """Supported social media platforms"""
    TIKTOK = "tiktok"
    INSTAGRAM_REELS = "instagram_reels"
    INSTAGRAM_STORIES = "instagram_stories"
    YOUTUBE_SHORTS = "youtube_shorts"
    YOUTUBE = "youtube"
    TWITTER = "twitter"


@dataclass
class PlatformSpecs:
    """Specifications for each social media platform"""
    name: str
    aspect_ratio: Tuple[int, int]  # (width, height)
    max_duration: int  # seconds
    min_duration: int  # seconds
    max_file_size: int  # MB
    resolution: Tuple[int, int]  # (width, height)
    frame_rate: int
    bitrate: str
    description: str


class SocialMediaOptimizer:
    """
    Optimizes videos for different social media platforms
    """

    PLATFORM_SPECS = {
        Platform.TIKTOK: PlatformSpecs(
            name="TikTok",
            aspect_ratio=(9, 16),
            max_duration=180,
            min_duration=3,
            max_file_size=287,
            resolution=(1080, 1920),
            frame_rate=30,
            bitrate="8M",
            description="Vertical short-form video"
        ),
        Platform.INSTAGRAM_REELS: PlatformSpecs(
            name="Instagram Reels",
            aspect_ratio=(9, 16),
            max_duration=90,
            min_duration=3,
            max_file_size=100,
            resolution=(1080, 1920),
            frame_rate=30,
            bitrate="6M",
            description="Vertical short-form video"
        ),
        Platform.INSTAGRAM_STORIES: PlatformSpecs(
            name="Instagram Stories",
            aspect_ratio=(9, 16),
            max_duration=15,
            min_duration=3,
            max_file_size=100,
            resolution=(1080, 1920),
            frame_rate=30,
            bitrate="6M",
            description="Vertical ephemeral content"
        ),
        Platform.YOUTUBE_SHORTS: PlatformSpecs(
            name="YouTube Shorts",
            aspect_ratio=(9, 16),
            max_duration=60,
            min_duration=1,
            max_file_size=100,
            resolution=(1080, 1920),
            frame_rate=30,
            bitrate="8M",
            description="Vertical short-form video"
        ),
        Platform.YOUTUBE: PlatformSpecs(
            name="YouTube",
            aspect_ratio=(16, 9),
            max_duration=43200,  # 12 hours
            min_duration=1,
            max_file_size=256000,  # 256GB
            resolution=(1920, 1080),
            frame_rate=30,
            bitrate="12M",
            description="Horizontal long-form video"
        ),
        Platform.TWITTER: PlatformSpecs(
            name="Twitter/X",
            aspect_ratio=(16, 9),
            max_duration=140,  # 2:20 minutes
            min_duration=1,
            max_file_size=512,
            resolution=(1280, 720),
            frame_rate=30,
            bitrate="8M",
            description="Horizontal short-form video"
        )
    }

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict]:
        """Load text overlay templates for different styles"""
        return {
            "modern": {
                "font": "Arial-Bold",
                "fontsize": 80,
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 3,
                "bg_color": (0, 0, 0, 0.7),
                "position": ("center", "bottom"),
                "animation": "fade_in"
            },
            "minimal": {
                "font": "Helvetica",
                "fontsize": 60,
                "color": "white",
                "stroke_color": None,
                "stroke_width": 0,
                "bg_color": None,
                "position": ("center", "center"),
                "animation": "slide_up"
            },
            "gaming": {
                "font": "Impact",
                "fontsize": 100,
                "color": "yellow",
                "stroke_color": "red",
                "stroke_width": 4,
                "bg_color": (255, 0, 0, 0.8),
                "position": ("center", "top"),
                "animation": "bounce"
            },
            "educational": {
                "font": "Georgia",
                "fontsize": 70,
                "color": "black",
                "stroke_color": "white",
                "stroke_width": 2,
                "bg_color": (255, 255, 255, 0.9),
                "position": ("center", "bottom"),
                "animation": "typewriter"
            }
        }

    def optimize_for_platform(self, video_path: Path, platform: Platform,
                            output_dir: Path, **kwargs) -> Dict[str, Any]:
        """
        Optimize video for specific social media platform

        Args:
            video_path: Input video path
            platform: Target platform
            output_dir: Output directory
            **kwargs: Additional optimization options

        Returns:
            Dictionary with optimization results
        """
        specs = self.PLATFORM_SPECS[platform]

        print(f"🎯 Optimizing for {specs.name} ({specs.description})")

        # Load video
        video = VideoFileClip(str(video_path))

        # Analyze current video
        analysis = self._analyze_video(video, specs)

        # Apply optimizations
        optimized_clips = []
        for clip_data in analysis['suggested_clips']:
            optimized = self._optimize_clip(video, clip_data, specs, **kwargs)
            if optimized:
                optimized_clips.append(optimized)

        # Generate output files
        results = self._generate_outputs(optimized_clips, specs, output_dir, platform)

        return {
            'platform': platform.value,
            'specs': {
                'aspect_ratio': specs.aspect_ratio,
                'resolution': specs.resolution,
                'max_duration': specs.max_duration
            },
            'analysis': analysis,
            'optimized_clips': optimized_clips,
            'output_files': results,
            'optimization_score': self._calculate_optimization_score(results)
        }

    def _analyze_video(self, video: VideoFileClip, specs: PlatformSpecs) -> Dict[str, Any]:
        """Analyze video and suggest optimal clips"""
        duration = video.duration
        width, height = video.size

        # Calculate aspect ratio compatibility
        current_ratio = width / height
        target_ratio = specs.aspect_ratio[0] / specs.aspect_ratio[1]
        ratio_compatibility = min(current_ratio, target_ratio) / max(current_ratio, target_ratio)

        # Suggest clip segments
        suggested_clips = []

        if duration <= specs.max_duration:
            # Video fits - suggest full video
            suggested_clips.append({
                'start_time': 0,
                'end_time': duration,
                'duration': duration,
                'reason': 'Full video fits platform specs'
            })
        else:
            # Need to split into segments
            segment_duration = min(specs.max_duration, duration / 3)  # Suggest 3 segments max

            for i in range(0, min(int(duration), specs.max_duration * 3), int(segment_duration)):
                end_time = min(i + segment_duration, duration)
                if end_time - i >= specs.min_duration:
                    suggested_clips.append({
                        'start_time': i,
                        'end_time': end_time,
                        'duration': end_time - i,
                        'reason': f'Segment {len(suggested_clips) + 1} of {min(3, int(duration / segment_duration) + 1)}'
                    })

        return {
            'original_duration': duration,
            'original_resolution': (width, height),
            'aspect_ratio_compatibility': ratio_compatibility,
            'suggested_clips': suggested_clips,
            'platform_fit_score': self._calculate_platform_fit(duration, (width, height), specs)
        }

    def _optimize_clip(self, video: VideoFileClip, clip_data: Dict, specs: PlatformSpecs,
                      add_text: bool = False, text_content: str = "", template: str = "modern") -> Optional[VideoFileClip]:
        """Optimize individual clip for platform"""
        try:
            # Extract clip segment
            clip = video.subclipped(clip_data['start_time'], clip_data['end_time'])

            # Resize for platform
            clip = self._resize_for_platform(clip, specs)

            # Add text overlay if requested
            if add_text and text_content:
                clip = self._add_text_overlay(clip, text_content, template)

            # Apply platform-specific enhancements
            clip = self._apply_platform_enhancements(clip, specs)

            return clip

        except Exception as e:
            print(f"Error optimizing clip: {e}")
            return None

    def _resize_for_platform(self, clip: VideoFileClip, specs: PlatformSpecs) -> VideoFileClip:
        """Resize clip to platform specifications"""
        target_width, target_height = specs.resolution

        # Get current dimensions
        current_width, current_height = clip.size

        # Calculate scaling
        width_ratio = target_width / current_width
        height_ratio = target_height / current_height
        scale_factor = min(width_ratio, height_ratio)

        # Resize video
        new_width = int(current_width * scale_factor)
        new_height = int(current_height * scale_factor)

        # Apply resize
        resized_clip = clip.resized((new_width, new_height))

        # Add padding if needed to match exact dimensions
        if new_width < target_width or new_height < target_height:
            # Center the video with padding
            pad_width = (target_width - new_width) // 2
            pad_height = (target_height - new_height) // 2

            # Create background
            bg_color = (0, 0, 0)  # Black background
            padded_clip = resized_clip.on_color(size=(target_width, target_height),
                                              color=bg_color,
                                              pos=(pad_width, pad_height))
            return padded_clip

        return resized_clip

    def _add_text_overlay(self, clip: VideoFileClip, text: str, template_name: str = "modern") -> VideoFileClip:
        """Add text overlay to clip"""
        if template_name not in self.templates:
            template_name = "modern"

        template = self.templates[template_name]

        # Create text clip
        txt_clip = TextClip(text, fontsize=template['fontsize'],
                           color=template['color'],
                           stroke_color=template['stroke_color'],
                           stroke_width=template['stroke_width'],
                           font=template['font'])

        # Position text
        if template['position'][0] == "center":
            x_pos = "center"
        else:
            x_pos = template['position'][0]

        if template['position'][1] == "center":
            y_pos = "center"
        elif template['position'][1] == "bottom":
            y_pos = clip.h - txt_clip.h - 50
        elif template['position'][1] == "top":
            y_pos = 50

        txt_clip = txt_clip.set_position((x_pos, y_pos))

        # Set duration to match video
        txt_clip = txt_clip.set_duration(clip.duration)

        # Add background if specified
        if template['bg_color']:
            # Create background rectangle
            bg_clip = txt_clip.on_color(size=(txt_clip.w + 40, txt_clip.h + 20),
                                      color=template['bg_color'][:3],
                                      col_opacity=template['bg_color'][3] if len(template['bg_color']) > 3 else 1)
            txt_clip = bg_clip

        # Composite with video
        return CompositeVideoClip([clip, txt_clip])

    def _apply_platform_enhancements(self, clip: VideoFileClip, specs: PlatformSpecs) -> VideoFileClip:
        """Apply platform-specific enhancements"""
        # Set frame rate
        clip = clip.set_fps(specs.frame_rate)

        # Add platform-specific effects
        if specs.aspect_ratio == (9, 16):  # Vertical platforms
            # Add subtle zoom effect for engagement
            clip = self._add_subtle_zoom(clip)

        return clip

    def _add_subtle_zoom(self, clip: VideoFileClip, zoom_factor: float = 1.05) -> VideoFileClip:
        """Add subtle zoom effect for better engagement"""
        def zoom_effect(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]

            # Calculate zoom
            zoom = 1 + (zoom_factor - 1) * (t / clip.duration)

            # Crop and resize
            crop_size = int(min(w, h) / zoom)
            x1 = (w - crop_size) // 2
            y1 = (h - crop_size) // 2
            x2 = x1 + crop_size
            y2 = y1 + crop_size

            cropped = frame[y1:y2, x1:x2]
            resized = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

            return resized

        return clip.fl(zoom_effect)

    def _generate_outputs(self, clips: List[VideoFileClip], specs: PlatformSpecs,
                         output_dir: Path, platform: Platform) -> List[Dict[str, Any]]:
        """Generate optimized output files"""
        output_files = []

        for i, clip in enumerate(clips):
            # Generate filename
            base_name = f"{platform.value}_clip_{i+1:02d}"
            output_path = output_dir / f"{base_name}.mp4"

            # Export with platform-specific settings
            try:
                clip.write_videofile(
                    str(output_path),
                    fps=specs.frame_rate,
                    bitrate=specs.bitrate,
                    codec='libx264',
                    audio_codec='aac',
                    audio_bitrate='128k',
                    verbose=False,
                    logger=None
                )

                # Get file info
                file_size_mb = output_path.stat().st_size / (1024 * 1024)

                output_files.append({
                    'path': str(output_path),
                    'filename': output_path.name,
                    'size_mb': round(file_size_mb, 2),
                    'duration': clip.duration,
                    'resolution': specs.resolution,
                    'platform': platform.value,
                    'specs_compliant': self._check_specs_compliance(output_path, specs)
                })

            except Exception as e:
                print(f"Error exporting clip {i+1}: {e}")
                continue

        return output_files

    def _check_specs_compliance(self, video_path: Path, specs: PlatformSpecs) -> Dict[str, bool]:
        """Check if exported video meets platform specifications"""
        video = VideoFileClip(str(video_path))

        compliance = {
            'duration': specs.min_duration <= video.duration <= specs.max_duration,
            'resolution': video.size == specs.resolution,
            'frame_rate': abs(video.fps - specs.frame_rate) < 1,  # Allow 1 fps tolerance
            'file_size': (video_path.stat().st_size / (1024 * 1024)) <= specs.max_file_size
        }

        video.close()
        return compliance

    def _calculate_platform_fit(self, duration: float, resolution: Tuple[int, int],
                               specs: PlatformSpecs) -> float:
        """Calculate how well video fits platform requirements"""
        duration_score = 1.0 if specs.min_duration <= duration <= specs.max_duration else 0.5

        # Aspect ratio compatibility
        current_ratio = resolution[0] / resolution[1]
        target_ratio = specs.aspect_ratio[0] / specs.aspect_ratio[1]
        ratio_score = min(current_ratio, target_ratio) / max(current_ratio, target_ratio)

        return (duration_score + ratio_score) / 2

    def _calculate_optimization_score(self, output_files: List[Dict]) -> float:
        """Calculate overall optimization score"""
        if not output_files:
            return 0.0

        total_score = 0
        for file_info in output_files:
            compliance = file_info.get('specs_compliant', {})
            compliance_score = sum(compliance.values()) / len(compliance)
            total_score += compliance_score

        return total_score / len(output_files)

    def batch_optimize(self, video_path: Path, platforms: List[Platform],
                      output_dir: Path, **kwargs) -> Dict[str, Any]:
        """
        Optimize video for multiple platforms at once

        Args:
            video_path: Input video path
            platforms: List of target platforms
            output_dir: Base output directory
            **kwargs: Additional options

        Returns:
            Results for all platforms
        """
        results = {}

        for platform in platforms:
            platform_output_dir = output_dir / platform.value
            platform_output_dir.mkdir(exist_ok=True)

            try:
                result = self.optimize_for_platform(video_path, platform, platform_output_dir, **kwargs)
                results[platform.value] = result
                print(f"✅ Optimized for {platform.value}: {len(result['output_files'])} files")
            except Exception as e:
                print(f"❌ Failed to optimize for {platform.value}: {e}")
                results[platform.value] = {'error': str(e)}

        return {
            'input_video': str(video_path),
            'platforms_processed': len([r for r in results.values() if 'error' not in r]),
            'total_files_generated': sum(len(r.get('output_files', [])) for r in results.values() if 'error' not in r),
            'platform_results': results
        }


def get_platform_specs() -> Dict[str, Dict]:
    """Get specifications for all supported platforms"""
    optimizer = SocialMediaOptimizer()
    return {
        platform.value: {
            'aspect_ratio': specs.aspect_ratio,
            'max_duration': specs.max_duration,
            'resolution': specs.resolution,
            'description': specs.description
        }
        for platform, specs in optimizer.PLATFORM_SPECS.items()
    }


if __name__ == "__main__":
    # Example usage
    optimizer = SocialMediaOptimizer()

    print("📱 Social Media Platform Specifications:")
    print("=" * 50)

    specs = get_platform_specs()
    for platform, spec in specs.items():
        print(f"\n🎯 {platform.upper()}")
        print(f"   Aspect Ratio: {spec['aspect_ratio'][0]}:{spec['aspect_ratio'][1]}")
        print(f"   Max Duration: {spec['max_duration']}s")
        print(f"   Resolution: {spec['resolution'][0]}x{spec['resolution'][1]}")
        print(f"   Description: {spec['description']}")

    print("
🚀 Ready for multi-platform optimization!"
