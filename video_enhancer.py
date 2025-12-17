#!/usr/bin/env python3
"""
Video Enhancer for LTW Video Editor Pro
Advanced video processing with color correction, stabilization, and effects
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Callable
from moviepy import VideoFileClip
from moviepy.video.fx import colorx, lum_contrast, blackwhite
from scipy import ndimage
from sklearn.cluster import KMeans
import colorsys
from tqdm import tqdm
import json
from datetime import datetime


class VideoEnhancer:
    """
    Advanced video enhancement with AI-powered corrections
    """

    def __init__(self):
        self.enhancement_presets = self._load_presets()

    def _load_presets(self) -> Dict[str, Dict]:
        """Load enhancement presets for different content types"""
        return {
            "cinematic": {
                "brightness": 1.1,
                "contrast": 1.2,
                "saturation": 1.3,
                "sharpness": 1.5,
                "color_temp": "warm",
                "vignette": 0.1,
                "grain": 0.05
            },
            "vibrant": {
                "brightness": 1.05,
                "contrast": 1.15,
                "saturation": 1.4,
                "sharpness": 1.2,
                "color_temp": "cool",
                "vignette": 0.0,
                "grain": 0.02
            },
            "natural": {
                "brightness": 1.0,
                "contrast": 1.1,
                "saturation": 1.0,
                "sharpness": 1.1,
                "color_temp": "neutral",
                "vignette": 0.0,
                "grain": 0.0
            },
            "dramatic": {
                "brightness": 0.9,
                "contrast": 1.4,
                "saturation": 0.8,
                "sharpness": 1.8,
                "color_temp": "cool",
                "vignette": 0.2,
                "grain": 0.1
            },
            "social_media": {
                "brightness": 1.1,
                "contrast": 1.2,
                "saturation": 1.3,
                "sharpness": 1.3,
                "color_temp": "warm",
                "vignette": 0.0,
                "grain": 0.01
            }
        }

    def enhance_video(self, video_path: Path, preset: str = "natural",
                     custom_settings: Dict = None, stabilization: bool = False) -> VideoFileClip:
        """
        Apply comprehensive video enhancement

        Args:
            video_path: Input video path
            preset: Enhancement preset to use
            custom_settings: Custom enhancement settings
            stabilization: Apply video stabilization

        Returns:
            Enhanced video clip
        """
        print(f"✨ Enhancing video with '{preset}' preset...")

        # Load video
        video = VideoFileClip(str(video_path))

        # Get enhancement settings
        settings = self.enhancement_presets.get(preset, self.enhancement_presets["natural"])
        if custom_settings:
            settings.update(custom_settings)

        # Analyze video for automatic corrections
        analysis = self._analyze_video_content(video)

        # Apply enhancements step by step
        enhanced = self._apply_color_correction(video, settings, analysis)
        enhanced = self._apply_sharpness(enhanced, settings)
        enhanced = self._apply_vignette(enhanced, settings)
        enhanced = self._apply_grain(enhanced, settings)

        if stabilization:
            enhanced = self._stabilize_video(enhanced)

        # Apply final touches
        enhanced = self._apply_final_touches(enhanced, settings)

        return enhanced

    def _analyze_video_content(self, video: VideoFileClip) -> Dict[str, Any]:
        """Analyze video content for intelligent corrections"""
        print("🔍 Analyzing video content...")

        # Sample frames for analysis
        sample_frames = []
        duration = video.duration
        fps = video.fps

        # Sample 10 frames throughout the video
        for i in range(10):
            time_point = (i / 9) * duration
            try:
                frame = video.get_frame(time_point)
                sample_frames.append(frame)
            except:
                continue

        if not sample_frames:
            return {'brightness': 0.5, 'contrast': 0.5, 'saturation': 0.5, 'dominant_colors': []}

        # Calculate average brightness
        brightness_values = []
        saturation_values = []

        for frame in sample_frames:
            # Convert to HSV for analysis
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

            # Brightness (V channel)
            brightness = np.mean(hsv[:, :, 2]) / 255.0
            brightness_values.append(brightness)

            # Saturation (S channel)
            saturation = np.mean(hsv[:, :, 1]) / 255.0
            saturation_values.append(saturation)

        avg_brightness = np.mean(brightness_values)
        avg_saturation = np.mean(saturation_values)

        # Calculate contrast (variance in brightness)
        contrast = np.std(brightness_values)

        # Find dominant colors
        dominant_colors = self._extract_dominant_colors(sample_frames[0])

        return {
            'brightness': avg_brightness,
            'contrast': contrast,
            'saturation': avg_saturation,
            'dominant_colors': dominant_colors,
            'needs_brightness_boost': avg_brightness < 0.4,
            'needs_contrast_boost': contrast < 0.1,
            'is_washed_out': avg_saturation < 0.2
        }

    def _extract_dominant_colors(self, frame: np.ndarray, n_colors: int = 5) -> List[Tuple[int, int, int]]:
        """Extract dominant colors from frame using K-means clustering"""
        # Reshape frame for clustering
        pixels = frame.reshape(-1, 3)

        # Reduce number of pixels for performance
        pixels_sample = pixels[np.random.choice(pixels.shape[0], min(10000, pixels.shape[0]), replace=False)]

        # Apply K-means clustering
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(pixels_sample)

        # Get dominant colors
        dominant_colors = []
        for center in kmeans.cluster_centers_:
            color = tuple(int(c) for c in center)
            dominant_colors.append(color)

        return dominant_colors

    def _apply_color_correction(self, video: VideoFileClip, settings: Dict,
                               analysis: Dict) -> VideoFileClip:
        """Apply intelligent color correction"""
        print("🎨 Applying color correction...")

        # Adjust brightness based on analysis
        brightness_mult = settings['brightness']
        if analysis['needs_brightness_boost']:
            brightness_mult *= 1.2

        # Adjust contrast
        contrast_mult = settings['contrast']
        if analysis['needs_contrast_boost']:
            contrast_mult *= 1.3

        # Adjust saturation
        saturation_mult = settings['saturation']
        if analysis['is_washed_out']:
            saturation_mult *= 1.4

        # Apply color temperature adjustment
        color_temp = settings.get('color_temp', 'neutral')
        temp_adjustment = self._get_color_temperature_adjustment(color_temp)

        def color_correction_effect(get_frame, t):
            frame = get_frame(t)

            # Convert to HSV for adjustments
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)

            # Apply saturation
            hsv[:, :, 1] *= saturation_mult

            # Apply brightness
            hsv[:, :, 2] *= brightness_mult

            # Ensure values stay in valid range
            hsv = np.clip(hsv, 0, 255)

            # Convert back to RGB
            corrected = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

            # Apply color temperature
            if temp_adjustment:
                corrected = self._apply_color_temperature(corrected, temp_adjustment)

            return corrected

        return video.fl(color_correction_effect)

    def _get_color_temperature_adjustment(self, temp: str) -> Optional[Dict[str, float]]:
        """Get color temperature adjustment values"""
        adjustments = {
            "warm": {"red": 1.1, "blue": 0.9},
            "cool": {"red": 0.9, "blue": 1.1},
            "neutral": None
        }
        return adjustments.get(temp)

    def _apply_color_temperature(self, frame: np.ndarray, adjustment: Dict[str, float]) -> np.ndarray:
        """Apply color temperature adjustment"""
        frame_float = frame.astype(np.float32) / 255.0

        # Adjust red and blue channels
        frame_float[:, :, 0] *= adjustment["blue"]   # Blue channel
        frame_float[:, :, 2] *= adjustment["red"]    # Red channel

        # Ensure values stay in valid range
        frame_float = np.clip(frame_float, 0, 1)

        return (frame_float * 255).astype(np.uint8)

    def _apply_sharpness(self, video: VideoFileClip, settings: Dict) -> VideoFileClip:
        """Apply sharpness enhancement"""
        sharpness_factor = settings.get('sharpness', 1.0)

        if sharpness_factor <= 1.0:
            return video

        def sharpen_effect(get_frame, t):
            frame = get_frame(t)

            # Create sharpening kernel
            kernel = np.array([[-1,-1,-1],
                             [-1, 9,-1],
                             [-1,-1,-1]]) * (sharpness_factor - 1)

            # Apply kernel
            sharpened = cv2.filter2D(frame, -1, kernel)

            # Blend with original
            result = cv2.addWeighted(frame, 1.5 - sharpness_factor, sharpened, sharpness_factor - 0.5, 0)

            return result

        return video.fl(sharpen_effect)

    def _apply_vignette(self, video: VideoFileClip, settings: Dict) -> VideoFileClip:
        """Apply vignette effect"""
        vignette_strength = settings.get('vignette', 0.0)

        if vignette_strength <= 0:
            return video

        def vignette_effect(get_frame, t):
            frame = get_frame(t)
            height, width = frame.shape[:2]

            # Create vignette mask
            x = np.linspace(-1, 1, width)
            y = np.linspace(-1, 1, height)
            xx, yy = np.meshgrid(x, y)
            radius = np.sqrt(xx**2 + yy**2)

            # Create vignette (darker at edges)
            vignette = 1 - vignette_strength * (radius ** 2)
            vignette = np.clip(vignette, 0.3, 1)  # Don't make it too dark

            # Apply vignette
            vignetted = frame.copy()
            for c in range(3):  # Apply to each color channel
                vignetted[:, :, c] = vignetted[:, :, c] * vignette

            return vignetted.astype(np.uint8)

        return video.fl(vignette_effect)

    def _apply_grain(self, video: VideoFileClip, settings: Dict) -> VideoFileClip:
        """Apply film grain effect"""
        grain_amount = settings.get('grain', 0.0)

        if grain_amount <= 0:
            return video

        def grain_effect(get_frame, t):
            frame = get_frame(t)

            # Generate random noise
            noise = np.random.normal(0, grain_amount * 50, frame.shape).astype(np.int16)

            # Add noise to frame
            grainy = frame.astype(np.int16) + noise

            # Clip values to valid range
            grainy = np.clip(grainy, 0, 255).astype(np.uint8)

            return grainy

        return video.fl(grain_effect)

    def _stabilize_video(self, video: VideoFileClip) -> VideoFileClip:
        """Apply video stabilization"""
        print("📹 Applying video stabilization...")

        # This is a simplified stabilization - in production, you'd use more sophisticated algorithms
        # For now, we'll implement a basic shake reduction

        def stabilization_effect(get_frame, t):
            frame = get_frame(t)

            # Convert to grayscale for motion estimation
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

            # Apply mild blur to reduce shake
            stabilized = cv2.GaussianBlur(frame, (3, 3), 0)

            return stabilized

        return video.fl(stabilization_effect)

    def _apply_final_touches(self, video: VideoFileClip, settings: Dict) -> VideoFileClip:
        """Apply final enhancement touches"""
        # Add subtle denoising
        def denoise_effect(get_frame, t):
            frame = get_frame(t)

            # Apply bilateral filter for noise reduction while preserving edges
            denoised = cv2.bilateralFilter(frame, 9, 75, 75)

            return denoised

        return video.fl(denoise_effect)

    def create_timelapse_effect(self, video: VideoFileClip, speed_factor: float = 2.0) -> VideoFileClip:
        """Create timelapse effect by speeding up video"""
        return video.speedx(factor=speed_factor)

    def create_slow_motion_effect(self, video: VideoFileClip, speed_factor: float = 0.5) -> VideoFileClip:
        """Create slow motion effect"""
        return video.speedx(factor=speed_factor)

    def add_dramatic_zoom(self, video: VideoFileClip, zoom_factor: float = 1.5,
                         zoom_duration: float = None) -> VideoFileClip:
        """Add dramatic zoom effect"""
        if zoom_duration is None:
            zoom_duration = video.duration

        def zoom_effect(get_frame, t):
            frame = get_frame(t)
            h, w = frame.shape[:2]

            # Calculate zoom progress
            progress = min(t / zoom_duration, 1.0)
            current_zoom = 1 + (zoom_factor - 1) * progress

            # Calculate crop size
            crop_size = int(min(w, h) / current_zoom)
            x1 = (w - crop_size) // 2
            y1 = (h - crop_size) // 2
            x2 = x1 + crop_size
            y2 = y1 + crop_size

            # Crop and resize
            cropped = frame[y1:y2, x1:x2]
            zoomed = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

            return zoomed

        return video.fl(zoom_effect)

    def apply_lut(self, video: VideoFileClip, lut_path: Optional[Path] = None,
                  preset: str = "cinematic") -> VideoFileClip:
        """Apply color LUT (Look Up Table) for cinematic looks"""
        # For now, implement basic color grading presets
        # In production, you'd load actual .cube LUT files

        lut_presets = {
            "cinematic": {
                "gamma": 1.2,
                "contrast": 1.1,
                "saturation": 0.9,
                "shadows": 1.1,
                "highlights": 0.9
            },
            "vintage": {
                "gamma": 1.1,
                "contrast": 1.0,
                "saturation": 0.7,
                "shadows": 1.2,
                "highlights": 0.8
            },
            "moody": {
                "gamma": 0.9,
                "contrast": 1.3,
                "saturation": 0.6,
                "shadows": 1.3,
                "highlights": 0.7
            }
        }

        if preset not in lut_presets:
            preset = "cinematic"

        settings = lut_presets[preset]

        def lut_effect(get_frame, t):
            frame = get_frame(t)
            frame_float = frame.astype(np.float32) / 255.0

            # Apply gamma correction
            frame_float = np.power(frame_float, 1/settings["gamma"])

            # Apply contrast
            frame_float = (frame_float - 0.5) * settings["contrast"] + 0.5

            # Apply saturation adjustment (simplified)
            hsv = cv2.cvtColor((frame_float * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] *= settings["saturation"]
            frame_float = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32) / 255.0

            # Clip and convert back
            frame_float = np.clip(frame_float, 0, 1)
            return (frame_float * 255).astype(np.uint8)

        return video.fl(lut_effect)

    def batch_enhance(self, video_paths: List[Path], preset: str = "social_media",
                      output_dir: Path = None) -> Dict[str, Any]:
        """
        Batch enhance multiple videos

        Args:
            video_paths: List of video paths
            preset: Enhancement preset
            output_dir: Output directory

        Returns:
            Enhancement results
        """
        if output_dir is None:
            output_dir = Path.cwd() / "enhanced_videos"
        output_dir.mkdir(exist_ok=True)

        results = []

        for video_path in tqdm(video_paths, desc="Enhancing videos"):
            try:
                # Enhance video
                enhanced = self.enhance_video(video_path, preset)

                # Generate output path
                output_path = output_dir / f"enhanced_{video_path.name}"

                # Export enhanced video
                enhanced.write_videofile(
                    str(output_path),
                    codec='libx264',
                    audio_codec='aac',
                    verbose=False,
                    logger=None
                )

                results.append({
                    'input': str(video_path),
                    'output': str(output_path),
                    'preset': preset,
                    'status': 'success'
                })

            except Exception as e:
                results.append({
                    'input': str(video_path),
                    'error': str(e),
                    'status': 'failed'
                })

        return {
            'total_processed': len(results),
            'successful': len([r for r in results if r['status'] == 'success']),
            'failed': len([r for r in results if r['status'] == 'failed']),
            'results': results
        }


def get_available_presets() -> List[str]:
    """Get list of available enhancement presets"""
    enhancer = VideoEnhancer()
    return list(enhancer.enhancement_presets.keys())


def enhance_video_quick(video_path: Path, preset: str = "social_media") -> VideoFileClip:
    """
    Quick enhancement function for simple use cases

    Args:
        video_path: Input video path
        preset: Enhancement preset

    Returns:
        Enhanced video clip
    """
    enhancer = VideoEnhancer()
    return enhancer.enhance_video(video_path, preset)


if __name__ == "__main__":
    # Example usage
    enhancer = VideoEnhancer()

    print("🎨 Video Enhancement Presets:")
    print("=" * 40)

    presets = get_available_presets()
    for preset in presets:
        settings = enhancer.enhancement_presets[preset]
        print(f"\n🎯 {preset.upper()}")
        print(f"   Brightness: {settings['brightness']}")
        print(f"   Contrast: {settings['contrast']}")
        print(f"   Saturation: {settings['saturation']}")
        print(f"   Sharpness: {settings['sharpness']}")
        print(f"   Color Temp: {settings['color_temp']}")

    print("
✨ Ready for professional video enhancement!"
