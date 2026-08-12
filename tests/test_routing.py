"""Model routing heuristics: right bucket, right model, silent when moot."""

from __future__ import annotations

from oshell.routing import RoutingConfig, classify, pick_model

CFG = RoutingConfig(
    enabled=True, fast_model="fast:4b", deep_model="deep:31b", vision_model="see:8b"
)


def test_classify_buckets():
    assert classify("thanks!") == "fast"
    assert classify("what's the capital of France?") == "fast"
    assert classify("explain why this deadlocks and design a fix") == "deep"
    assert classify("```python\ndef f(): ...\n``` what's wrong?") == "deep"
    assert classify("x" * 700) == "deep"  # long prompts imply real work
    assert classify("look", has_images=True) == "vision"


def test_pick_model_switches_with_reason():
    got = pick_model("refactor this module step by step", False, CFG, "fast:4b")
    assert got == ("deep:31b", "this one deserves the big model")
    got = pick_model("hi", False, CFG, "deep:31b")
    assert got == ("fast:4b", "quick question, fast model")
    got = pick_model("what is this?", True, CFG, "fast:4b")
    assert got is not None and got[0] == "see:8b"


def test_pick_model_stays_put_when_moot():
    assert pick_model("hi", False, CFG, "fast:4b") is None  # already there
    assert pick_model("hi", False, RoutingConfig(enabled=False), "m") is None  # disabled
    # Empty slot: nothing configured for the bucket -> no switch.
    sparse = RoutingConfig(enabled=True, deep_model="deep:31b")
    assert pick_model("hi", False, sparse, "current") is None
