"""Tests for the ambient effects models (pure logic, no Textual needed)."""

from __future__ import annotations

import pytest

pytest.importorskip("textual")  # ambient lives in the tui package

from oshell.tui import ambient  # noqa: E402


def test_aurora_cycles_through_palette():
    seen = {ambient.aurora_color(i) for i in range(len(ambient.AURORA) * 2)}
    assert seen == set(ambient.AURORA)
    assert ambient.aurora_color(0) == ambient.aurora_color(len(ambient.AURORA))


def test_ember_color_by_tool_kind():
    assert ambient.ember_color_for("web_search") == ambient.EMBER_COLORS["net"]
    assert ambient.ember_color_for("browser_click") == ambient.EMBER_COLORS["net"]
    assert ambient.ember_color_for("remember") == ambient.EMBER_COLORS["memory"]
    assert ambient.ember_color_for("recall") == ambient.EMBER_COLORS["memory"]
    assert ambient.ember_color_for("list_dir") == ambient.EMBER_COLORS["local"]


def test_ember_glyph_fades_then_dies():
    assert ambient.ember_glyph(0.0) == ambient.EMBER_FRAMES[0]
    # Monotonically "cooler" over its life, then None.
    mid = ambient.ember_glyph(ambient.EMBER_SECONDS * 0.7)
    assert mid in ambient.EMBER_FRAMES
    assert ambient.ember_glyph(ambient.EMBER_SECONDS) is None
    assert ambient.ember_glyph(99.0) is None


def test_fireflies_deterministic_and_bounded():
    a = ambient.fireflies_markup(60, 42)
    b = ambient.fireflies_markup(60, 42)
    assert a == b  # deterministic in (width, tick)
    assert any(g in a for g in ("✦", "✧", "·"))
    # Different ticks -> the flies move.
    assert ambient.fireflies_markup(60, 42) != ambient.fireflies_markup(60, 60)


def test_starfield_steps_and_renders():
    m = ambient.StarfieldModel(n_stars=30, seed=7)
    phases = [s.phase for s in m.stars]
    for _ in range(20):
        m.step()
    assert [s.phase for s in m.stars] != phases  # twinkle advanced
    text = m.render(60, 18)
    lines = text.plain.split("\n")
    assert len(lines) == 18
    assert all(len(ln) <= 60 for ln in lines)
    # Stars actually rendered somewhere.
    assert any(ch in text.plain for ch in ("·", "✧", "✦", "*"))


def test_starfield_renders_centered_dream_and_wake_hint():
    m = ambient.StarfieldModel(n_stars=10, seed=1)
    dream = "a clock made of warm rain drifts over the creek"
    text = m.render(80, 20, dream=dream, done=True)
    assert "💭" in text.plain
    assert "warm rain" in text.plain
    assert "press any key to wake" in text.plain


def test_starfield_survives_hostile_dream_text():
    # Brackets / markup-ish content must render inert (explicit-style Text).
    m = ambient.StarfieldModel(n_stars=5, seed=2)
    text = m.render(60, 12, dream="[bold]not markup[/bold] \\[x] [/dim]", done=True)
    assert "[bold]not markup[/bold]" in text.plain


def test_starfield_comet_lifecycle():
    m = ambient.StarfieldModel(n_stars=5, seed=3)
    # Step long enough that a comet is born and dies without incident.
    saw_comet = False
    for _ in range(600):
        m.step()
        if m.comet is not None:
            saw_comet = True
            assert 0 <= m.comet.x <= 1 and 0 <= m.comet.y <= 1
    assert saw_comet


# ── weather, bursts, constellations, density ──────────────────────────────────


def test_sky_mood_rain_snow_clear():
    # Two storm words in the recent topics -> rain.
    assert ambient.sky_mood(["an error everywhere", "another traceback"], month=6) == "rain"
    # December, calm session -> snow.
    assert ambient.sky_mood(["a calm chat about gardens"], month=12) == "snow"
    # Neither -> a clear night.
    assert ambient.sky_mood(["a calm chat about gardens"], month=6) == "clear"
    # A stormy session outranks the season.
    assert ambient.sky_mood(["error", "crash"], month=12) == "rain"
    # One stray mention isn't a storm.
    assert ambient.sky_mood(["fixed one error, all good"], month=6) == "clear"


def test_burst_scatters_then_burns_out():
    early = ambient.burst_markup(60, 0.0)
    assert early and any(g in early for g in "✷✶✧∗·")
    assert ambient.burst_markup(60, 0.0) == early  # deterministic per frame
    late = ambient.burst_markup(60, ambient.BURST_SECONDS * 0.9)
    assert late is not None  # still sparking near the end...
    assert ambient.burst_markup(60, ambient.BURST_SECONDS) is None  # ...then spent
    assert ambient.burst_markup(60, -0.1) is None


def test_constellation_line_static_and_faint():
    line = ambient.constellation_line(76, seed=3)
    assert line == ambient.constellation_line(76, seed=3)  # static, not animated
    assert any(g in line for g in "·✧✦")
    assert ambient.constellation_line(76, seed=4) != line  # seed varies the sky


def test_starfield_rain_falls_and_renders():
    sky = ambient.StarfieldModel(seed=1, weather="rain")
    assert sky.flakes
    y0 = [f.y for f in sky.flakes]
    sky.step()
    assert any(f.y != y for f, y in zip(sky.flakes, y0, strict=True))  # the rain moves
    assert "╱" in sky.render(40, 12).plain


def test_starfield_snow_renders_flakes():
    sky = ambient.StarfieldModel(seed=2, weather="snow")
    assert sky.flakes
    for _ in range(3):
        sky.step()
    assert any(g in sky.render(48, 14).plain for g in ("❄", "✻"))


def test_starfield_density_scales_the_sky():
    assert not ambient.StarfieldModel(seed=3, density=0.0).stars  # empty night
    assert len(ambient.StarfieldModel(seed=4, density=2.0).stars) == 180
    rain = ambient.StarfieldModel(seed=5, weather="rain", density=2.0)
    assert len(rain.flakes) == 52  # weather scales with density too


def test_clear_sky_has_no_flakes():
    assert ambient.StarfieldModel(seed=6).flakes == []


# ── moods: the idle strip's user-pickable ambience ────────────────────────────


def test_every_mood_renders_deterministically():
    for mood in ambient.MOODS:
        a = ambient.mood_markup(mood, 60, tick=17)
        b = ambient.mood_markup(mood, 60, tick=17)
        assert a == b, mood  # pure in (width, tick)
        assert isinstance(a, str)


def test_moods_animate_over_time():
    for mood in ambient.MOODS:
        if mood in ("none",):
            continue
        frames = {ambient.mood_markup(mood, 60, t) for t in range(0, 40, 3)}
        assert len(frames) > 1, f"{mood} should move"


def test_mood_signatures():
    assert "╱" in ambient.mood_markup("rain", 60, 5)
    assert any(g in ambient.mood_markup("snow", 60, 5) for g in ("❄", "✻"))
    assert "─" in ambient.mood_markup("aurora", 60, 5)
    assert "~" in ambient.mood_markup("ocean", 60, 5) or "≈" in ambient.mood_markup("ocean", 60, 5)
    assert ambient.mood_markup("none", 60, 5) == ""
    # unknown mood falls back to fireflies, never errors
    assert ambient.mood_markup("volcano", 60, 5) == ambient.fireflies_markup(60, 5)


def test_mood_list_is_stable():
    # The picker + config docs promise these names.
    assert set(ambient.MOODS) == {
        "fireflies", "rain", "snow", "aurora", "ocean",
        "starfield", "embers", "matrix", "none",
    }
