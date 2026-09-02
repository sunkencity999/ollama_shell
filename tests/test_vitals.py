"""The vitals tile: probes never raise, rendering is pure and width-aware."""

from __future__ import annotations

from oshell.tui import vitals


def test_probes_are_best_effort_and_never_raise():
    cpu = vitals.cpu_percent()
    assert cpu is None or 0.0 <= cpu <= 100.0
    used, total = vitals.memory_gb()
    assert used is None or used >= 0
    assert total is None or total > 0
    assert vitals.load1() is None or vitals.load1() >= 0
    assert isinstance(vitals.uptime_str(), str)


def test_sparkline_and_bar_shapes():
    assert vitals.sparkline([0, 50, 100], 3) == "▁▅█"
    assert vitals.sparkline([100], 4) == "   █"  # right-aligned, padded
    assert vitals.sparkline([], 3) == "   "
    assert vitals.bar(50, 10) == "▰▰▰▰▰▱▱▱▱▱"
    assert vitals.bar(None, 4) == "▱▱▱▱"


def test_render_vitals_mentions_everything():
    s = vitals.VitalsSample(
        cpu_pct=12.0,
        mem_used_gb=56.0,
        mem_total_gb=137.0,
        load1=3.2,
        loaded=[{"name": "gemma4:26b", "size": 28e9, "size_vram": 28e9}],
        tok_s=41.0,
        ctx_fill=0.34,
        uptime="3h 24m",
        n_tools=29,
        n_net=0,
    )
    text = vitals.render_vitals(s, [10, 12], [40, 41], [38, 41], width=60, colors={}).plain
    for needle in ("cpu", "12%", "mem", "41%", "56/137 GB", "gemma4:26b", "100% GPU",
                   "41 tok/s", "34%", "29 tools", "fully local", "up 3h 24m", "load 3.2"):
        assert needle in text, needle
    empty = vitals.render_vitals(vitals.VitalsSample(), [], [], [], width=30, colors={}).plain
    assert "nothing loaded" in empty and "—" in empty
    assert all(len(line) <= 60 for line in text.split("\n"))


def test_take_sample_tolerates_a_provider_without_ps():
    class _P:
        def loaded_models(self):
            raise RuntimeError("no /api/ps here")

    s = vitals.take_sample(_P(), tok_s=None, ctx_fill=0.1, n_tools=2, n_net=1)
    assert s.loaded == [] and s.n_tools == 2 and s.n_net == 1
