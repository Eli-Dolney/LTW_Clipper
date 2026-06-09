"""Tests for the channel template schema and manager."""

from __future__ import annotations

from pathlib import Path

from src.core.templates import ChannelTemplate, TemplateManager
from src.core.templates.models import ScoringWeightsModel


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILTIN_DIR = REPO_ROOT / "assets" / "templates"


def test_builtin_templates_load_and_validate() -> None:
    mgr = TemplateManager(BUILTIN_DIR)
    names = mgr.names()
    assert "Game Dev Tutorial" in names
    assert "Gaming" in names
    assert "Geopolitics" in names
    assert "AI Channel" in names
    # All shipped templates must be flagged builtin and have niche-specific hooks.
    for tpl in mgr.all():
        assert tpl.builtin is True
        assert tpl.hook_phrases, f"{tpl.name} has no hook phrases"
        assert tpl.voice.persona, f"{tpl.name} has no persona"


def test_save_and_delete_user_template(tmp_path: Path) -> None:
    mgr = TemplateManager(tmp_path)
    tpl = ChannelTemplate(name="My Custom", niche="custom", hook_phrases=["watch this"])
    path = mgr.save(tpl)
    assert path.exists()
    assert tpl.builtin is False

    # Reload from disk to prove persistence.
    mgr2 = TemplateManager(tmp_path)
    loaded = mgr2.get("My Custom")
    assert loaded is not None
    assert loaded.hook_phrases == ["watch this"]

    assert mgr2.delete("My Custom") is True
    assert mgr2.get("My Custom") is None


def test_builtin_cannot_be_deleted(tmp_path: Path) -> None:
    mgr = TemplateManager(tmp_path)
    builtin = ChannelTemplate(name="Locked", builtin=True)
    # Simulate a shipped builtin by writing it directly, then reloading.
    (tmp_path / "locked.json").write_text(builtin.model_dump_json(indent=2), encoding="utf-8")
    mgr.reload()
    assert mgr.get("Locked") is not None
    assert mgr.delete("Locked") is False


def test_export_import_roundtrip(tmp_path: Path) -> None:
    mgr = TemplateManager(tmp_path / "store")
    tpl = ChannelTemplate(
        name="Exported",
        scoring_weights=ScoringWeightsModel(audio=0.5, hook_phrase=0.2),
    )
    mgr.save(tpl)
    dest = tmp_path / "exported.json"
    assert mgr.export("Exported", dest) is True

    other = TemplateManager(tmp_path / "store2")
    imported = other.import_file(dest)
    assert imported is not None
    assert imported.scoring_weights.audio == 0.5


def test_from_preset_dict_upgrades_legacy_preset() -> None:
    legacy = {
        "name": "Gaming Clips",
        "category": "gaming",
        "description": "Optimized for gaming content",
        "clip_duration": 20,
        "scene_detection": True,
        "max_clips": 15,
        "platforms": ["tiktok", "youtube_shorts"],
        "lut_name": "Gaming_Vibrant",
    }
    tpl = ChannelTemplate.from_preset_dict(legacy)
    assert tpl.name == "Gaming Clips"
    assert tpl.niche == "gaming"
    assert tpl.clip_duration == 20.0
    assert tpl.look.lut_name == "Gaming_Vibrant"
    assert "tiktok" in tpl.platforms


def test_voice_prompt_block_renders() -> None:
    tpl = next(t for t in TemplateManager(BUILTIN_DIR).all() if t.name == "Geopolitics")
    block = tpl.voice.prompt_block()
    assert "persona" in block.lower()
    assert "tone" in block.lower()
