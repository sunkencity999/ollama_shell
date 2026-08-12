"""Setup wizard core: hardware-tiered model recommendations."""

from __future__ import annotations

from oshell.setup import recommend_models


def test_tiers_scale_with_ram():
    small = recommend_models(8, [])
    mid = recommend_models(16, [])
    big = recommend_models(64, [])
    assert small["tier"] == "under 12 GB"
    assert small["slots"]["deep"]["model"] == "gemma3:4b"  # one model does everything
    assert mid["slots"]["deep"]["model"] == "qwen3:8b"
    assert big["slots"]["deep"]["model"] == "qwen3:30b"
    assert big["slots"]["vision"]["model"] == "gemma3:27b"


def test_installed_detection_tolerates_quant_suffixes():
    plan = recommend_models(16, ["qwen3:8b-q4_K_M", "unrelated:7b"])
    assert plan["slots"]["deep"]["installed"] is True  # family:size matches
    assert plan["slots"]["fast"]["installed"] is False


def test_exact_name_counts_as_installed():
    plan = recommend_models(16, ["gemma3:4b"])
    assert plan["slots"]["fast"]["installed"] is True
