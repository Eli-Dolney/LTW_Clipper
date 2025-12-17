"""
LTW Video Editor Pro - Preset Manager
Save and load processing presets
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class Preset:
    """Video processing preset"""
    name: str
    category: str = "custom"
    description: str = ""
    
    # Splitting settings
    clip_duration: int = 30
    quality: str = "youtube_hd"
    scene_detection: bool = False
    min_scene_duration: int = 10
    naming_pattern: str = "{name}_part_{num:03d}"
    
    # Opus Clip settings
    platforms: List[str] = field(default_factory=lambda: ["youtube_shorts"])
    ai_highlights: bool = True
    enhancement_preset: str = "social_media"
    max_clips: int = 10
    add_captions: bool = False
    
    # Resolve settings
    generate_resolve_project: bool = True
    lut_name: Optional[str] = None
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert preset to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Preset':
        """Create preset from dictionary"""
        # Filter out any keys that aren't in the dataclass
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


class PresetManager:
    """Manage video processing presets"""
    
    def __init__(self, presets_dir: Optional[Path] = None):
        if presets_dir is None:
            # Default to presets directory in project
            self.presets_dir = Path(__file__).parent.parent.parent / "presets"
        else:
            self.presets_dir = Path(presets_dir)
            
        self.presets_dir.mkdir(exist_ok=True)
        self._presets: Dict[str, Preset] = {}
        
        # Load built-in presets
        self._load_builtin_presets()
        
        # Load user presets
        self._load_user_presets()
        
    def _load_builtin_presets(self):
        """Load built-in default presets"""
        builtin = [
            Preset(
                name="Sports Montage",
                category="sports",
                description="Fast-paced clips for sports highlights",
                clip_duration=15,
                quality="youtube_4k",
                scene_detection=True,
                platforms=["tiktok", "instagram_reels", "youtube_shorts"],
                ai_highlights=True,
                enhancement_preset="vibrant",
                max_clips=20,
                lut_name="Sports_Pop"
            ),
            Preset(
                name="Tutorial Clips",
                category="educational",
                description="Longer segments for educational content",
                clip_duration=45,
                quality="youtube_hd",
                scene_detection=False,
                platforms=["youtube_shorts", "youtube"],
                ai_highlights=False,
                enhancement_preset="clean",
                max_clips=15,
                lut_name=None
            ),
            Preset(
                name="Highlight Reel",
                category="general",
                description="AI-powered best moments extraction",
                clip_duration=30,
                quality="youtube_hd",
                scene_detection=True,
                platforms=["tiktok", "instagram_reels", "youtube_shorts"],
                ai_highlights=True,
                enhancement_preset="social_media",
                max_clips=10,
                add_captions=True
            ),
            Preset(
                name="Quick TikTok",
                category="social",
                description="Short, punchy clips for TikTok",
                clip_duration=15,
                quality="youtube_hd",
                scene_detection=True,
                platforms=["tiktok"],
                ai_highlights=True,
                enhancement_preset="vibrant",
                max_clips=25,
                add_captions=True
            ),
            Preset(
                name="Gaming Clips",
                category="gaming",
                description="Optimized for gaming content",
                clip_duration=20,
                quality="youtube_4k",
                scene_detection=True,
                platforms=["tiktok", "youtube_shorts"],
                ai_highlights=True,
                enhancement_preset="gaming",
                max_clips=15,
                lut_name="Gaming_Vibrant"
            ),
            Preset(
                name="Cinematic",
                category="film",
                description="Film-style color grading and pacing",
                clip_duration=60,
                quality="youtube_4k",
                scene_detection=True,
                platforms=["youtube"],
                ai_highlights=False,
                enhancement_preset="cinematic",
                max_clips=5,
                lut_name="Cinematic_Teal"
            ),
        ]
        
        for preset in builtin:
            self._presets[preset.name] = preset
            
    def _load_user_presets(self):
        """Load user-created presets from disk"""
        for preset_file in self.presets_dir.glob("*.json"):
            try:
                with open(preset_file, 'r') as f:
                    data = json.load(f)
                    preset = Preset.from_dict(data)
                    self._presets[preset.name] = preset
            except Exception as e:
                print(f"Warning: Failed to load preset {preset_file.name}: {e}")
                
    def save_preset(self, preset: Preset) -> bool:
        """Save a preset to disk"""
        try:
            preset.modified_at = datetime.now().isoformat()
            preset_file = self.presets_dir / f"{preset.name.replace(' ', '_').lower()}.json"
            
            with open(preset_file, 'w') as f:
                json.dump(preset.to_dict(), f, indent=2)
                
            self._presets[preset.name] = preset
            return True
        except Exception as e:
            print(f"Error saving preset: {e}")
            return False
            
    def delete_preset(self, name: str) -> bool:
        """Delete a preset"""
        if name not in self._presets:
            return False
            
        # Don't delete built-in presets
        preset_file = self.presets_dir / f"{name.replace(' ', '_').lower()}.json"
        if preset_file.exists():
            preset_file.unlink()
            
        del self._presets[name]
        return True
        
    def get_preset(self, name: str) -> Optional[Preset]:
        """Get a preset by name"""
        return self._presets.get(name)
        
    def get_all_presets(self) -> List[Preset]:
        """Get all presets"""
        return list(self._presets.values())
        
    def get_presets_by_category(self, category: str) -> List[Preset]:
        """Get presets by category"""
        return [p for p in self._presets.values() if p.category == category]
        
    def get_categories(self) -> List[str]:
        """Get list of all categories"""
        return list(set(p.category for p in self._presets.values()))
        
    def create_preset_from_settings(self, name: str, settings: Dict[str, Any],
                                     category: str = "custom", 
                                     description: str = "") -> Preset:
        """Create a new preset from current settings"""
        preset = Preset(
            name=name,
            category=category,
            description=description,
            **settings
        )
        self.save_preset(preset)
        return preset
        
    def export_preset(self, name: str, filepath: Path) -> bool:
        """Export a preset to a file"""
        preset = self.get_preset(name)
        if not preset:
            return False
            
        try:
            with open(filepath, 'w') as f:
                json.dump(preset.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting preset: {e}")
            return False
            
    def import_preset(self, filepath: Path) -> Optional[Preset]:
        """Import a preset from a file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                preset = Preset.from_dict(data)
                self._presets[preset.name] = preset
                self.save_preset(preset)
                return preset
        except Exception as e:
            print(f"Error importing preset: {e}")
            return None

