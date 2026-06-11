"""Tests for the ffmpeg transition/SFX filtergraph builder (no ffmpeg needed)."""

from __future__ import annotations

import pytest

from src.core.render.transitions import (
    build_filtergraph,
    compute_offsets,
    resolve_transition,
)


def test_resolve_transition_maps_and_defaults() -> None:
    assert resolve_transition("fade_black") == "fadeblack"
    assert resolve_transition("wipeleft") == "wipeleft"  # already an ffmpeg name
    assert resolve_transition("nonsense") == "fade"


def test_compute_offsets_chains_correctly() -> None:
    # Three 10s clips, 0.5s transitions.
    offsets = compute_offsets([10.0, 10.0, 10.0], 0.5)
    # offset_1 = 10 - 0.5 = 9.5 ; offset_2 = 20 - 1.0 = 19.0
    assert offsets == [9.5, 19.0]


def test_single_clip_has_no_xfade() -> None:
    graph, vlabel, alabel = build_filtergraph([12.0], with_audio=True)
    assert "xfade" not in graph
    assert vlabel == "v0n"
    assert alabel == "abase"
    assert "[0:a]anull[abase]" in graph


def test_multi_clip_video_and_audio_chain() -> None:
    graph, vlabel, alabel = build_filtergraph(
        [8.0, 8.0, 8.0], transition="dissolve", transition_dur=0.5, with_audio=True
    )
    assert vlabel == "vout"
    assert alabel == "abase"
    assert graph.count("xfade") == 2
    assert "transition=dissolve" in graph
    assert graph.count("acrossfade") == 2
    assert "offset=7.5" in graph  # 8 - 0.5


def test_sfx_adds_split_delay_and_mix() -> None:
    graph, _v, alabel = build_filtergraph(
        [8.0, 8.0, 8.0], transition_dur=0.5, with_audio=True, sfx=True
    )
    assert alabel == "aout"
    assert "asplit=2" in graph
    assert "adelay=" in graph
    assert "amix=inputs=3" in graph  # base + 2 sfx hits


def test_no_audio_returns_none_label() -> None:
    _graph, _v, alabel = build_filtergraph([8.0, 8.0], with_audio=False)
    assert alabel is None


def test_empty_raises() -> None:
    with pytest.raises(ValueError):
        build_filtergraph([])
