"""Tests for Edit Suite — beat sync, audio mix graphs, reference analysis."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.edit_suite.audio_mixer import AudioMixOptions, build_audio_mix_filtergraph
from src.core.edit_suite.composer import plan_clip_durations
from src.core.edit_suite.models import BeatMap, EditStyleRecipe, ReferenceAnalysis
from src.core.edit_suite.reference_analyzer import (
    ReferenceAnalyzer,
    compute_cut_stats,
    infer_style_tag,
)


def test_compute_cut_stats() -> None:
    stats = compute_cut_stats([2.0, 4.5, 7.0], duration=10.0)
    assert stats["cut_count"] == 3
    assert stats["cuts_per_minute"] == 18.0
    assert 2.0 < stats["avg_shot_length"] < 3.5


def test_infer_style_tag_sports() -> None:
    assert infer_style_tag({"cuts_per_minute": 30, "avg_shot_length": 1.5}, 10) == "sports"


def test_infer_style_tag_cinematic() -> None:
    assert infer_style_tag({"cuts_per_minute": 8, "avg_shot_length": 4.0}, 2) == "cinematic"


def test_beat_map_intervals() -> None:
    bm = BeatMap(beats=[0.0, 0.5, 1.0, 1.5, 2.0], tempo=120.0, total_beats=5)
    ivs = bm.intervals()
    assert len(ivs) == 4
    assert ivs[0] == (0.0, 0.5)


def test_plan_clip_durations_with_beats() -> None:
    bm = BeatMap(beats=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5], tempo=120.0, total_beats=6)
    clips = [Path("a.mp4"), Path("b.mp4")]
    durs = plan_clip_durations(clips, bm, beats_per_clip=2)
    assert len(durs) == 2
    assert all(d > 0 for d in durs)


def test_plan_clip_durations_fallback() -> None:
    clips = [Path("a.mp4"), Path("b.mp4"), Path("c.mp4")]
    durs = plan_clip_durations(clips, None, fallback_duration=1.8)
    assert durs == [1.8, 1.8, 1.8]


def test_audio_mix_filtergraph_dialog_and_music() -> None:
    graph, label = build_audio_mix_filtergraph(
        duration=30.0,
        has_dialog=True,
        has_music=True,
        options=AudioMixOptions(duck_music=True),
    )
    assert "sidechaincompress" in graph
    assert "amix" in graph
    assert label == "aout"


def test_audio_mix_filtergraph_music_only() -> None:
    graph, label = build_audio_mix_filtergraph(
        duration=15.0,
        has_dialog=False,
        has_music=True,
        options=AudioMixOptions(duck_music=False),
    )
    assert "atrim" in graph
    assert label == "aout"


def test_audio_mix_with_announcer() -> None:
    graph, _ = build_audio_mix_filtergraph(
        duration=20.0,
        has_dialog=True,
        has_music=True,
        has_announcer=True,
    )
    assert "[ann]" in graph
    assert "amix=inputs=3" in graph


def test_edit_style_recipe_defaults() -> None:
    sports = EditStyleRecipe.sports_default()
    cine = EditStyleRecipe.cinematic_default()
    assert sports.cuts_per_minute > cine.cuts_per_minute
    assert sports.transition_dur < cine.transition_dur


def test_reference_analysis_round_trip(tmp_path: Path) -> None:
    analysis = ReferenceAnalysis(
        recipe=EditStyleRecipe.sports_default(),
        cut_timestamps=[1.0, 2.5, 4.0],
        audio_peak_timestamps=[0.5, 3.0],
    )
    path = tmp_path / "recipe.json"
    ReferenceAnalyzer().save(analysis, path)
    loaded = ReferenceAnalyzer().load(path)
    assert loaded.recipe.style_tag == "sports"
    assert len(loaded.cut_timestamps) == 3


def test_beat_map_json_round_trip(tmp_path: Path) -> None:
    bm = BeatMap(source="song.mp3", tempo=128.0, total_beats=3, beats=[0.0, 0.5, 1.0])
    path = tmp_path / "beats.json"
    path.write_text(json.dumps(bm.model_dump(mode="json")), encoding="utf-8")
    restored = BeatMap.model_validate_json(path.read_text(encoding="utf-8"))
    assert restored.tempo == 128.0
    assert len(restored.beats) == 3
