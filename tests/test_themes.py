"""Themes: Omarchy-format palettes → Textual / Rich / terminal exports."""

from __future__ import annotations

from pathlib import Path

import pytest

from oshell import themes


def test_all_bundled_palettes_load_and_are_well_formed():
    names = themes.builtin_names()
    assert len(names) >= 22  # Omarchy's set ships built in
    for name in ("tokyo-night", "osaka-jade", "matte-black", "catppuccin-latte"):
        assert name in names
    for name, p in themes.list_palettes().items():
        assert p.name == name
        assert p.mode in ("dark", "light")
        assert p.source == "builtin"
        for c in p.ansi():
            assert c.startswith("#") and len(c) == 7
    assert themes.get_palette("catppuccin-latte").mode == "light"


def test_minimal_colors_toml_is_filled_in_sensibly():
    p = themes.palette_from_dict(
        "mini", {"accent": "#ff0000", "background": "#000000", "foreground": "#ffffff"}
    )
    assert p.blue == "#ff0000"  # chroma falls back sideways to the accent
    assert p.lighter_background != p.background  # ladder derived
    assert p.bright_red == p.red
    assert p.dark


def test_missing_required_color_and_bad_hex_fail_loudly():
    with pytest.raises(ValueError, match="missing required"):
        themes.palette_from_dict("x", {"accent": "#ff0000"})
    with pytest.raises(ValueError, match="not a #rrggbb"):
        themes.palette_from_dict(
            "x", {"accent": "red", "background": "#000000", "foreground": "#ffffff"}
        )


def test_parse_colors_toml_handles_omarchy_files():
    text = 'mode = "dark"\n\naccent = "#7aa2f7"\n# a comment\nhyprland_active_border = "rgba(x)"\n'
    data = themes.parse_colors_toml(text)
    assert data["accent"] == "#7aa2f7" and data["mode"] == "dark"
    with pytest.raises(ValueError):
        themes.parse_colors_toml("this is = = not toml [")


def test_user_theme_dir_adds_and_overrides(tmp_path):
    d = tmp_path / "themes"
    d.mkdir()
    (d / "mine.toml").write_text(
        'accent = "#123456"\nbackground = "#000000"\nforeground = "#eeeeee"\n'
    )
    # A dir-style Omarchy theme (name/colors.toml) works too, and a user file
    # named like a bundled theme overrides it.
    (d / "foo").mkdir()
    (d / "foo" / "colors.toml").write_text(
        'mode = "light"\naccent = "#111111"\nbackground = "#ffffff"\nforeground = "#000000"\n'
    )
    (d / "tokyo-night.toml").write_text(
        'accent = "#abcdef"\nbackground = "#000000"\nforeground = "#eeeeee"\n'
    )
    (d / "broken.toml").write_text("nope")
    pals = themes.list_palettes(d)
    assert pals["mine"].accent == "#123456"
    assert pals["foo"].mode == "light" and pals["foo"].source.endswith("colors.toml")
    assert pals["tokyo-night"].accent == "#abcdef"  # user wins
    assert "broken" not in pals  # a bad file never breaks startup
    assert themes.get_palette("mine", d).accent == "#123456"
    assert themes.get_palette("dracula", d) is None  # Textual-only names have no palette


def test_textual_theme_has_distinct_roles():
    pytest.importorskip("textual")
    for p in themes.list_palettes().values():
        t = themes.to_textual_theme(p)
        assert t.name == p.name
        assert t.primary == p.accent
        assert t.background == p.background
        assert t.dark == p.dark
        assert t.variables["border"] == p.accent


def test_rich_theme_defines_the_semantic_styles():
    from rich.console import Console

    p = themes.get_palette("gruvbox")
    console = Console(theme=themes.to_rich_theme(p), record=True, width=60)
    console.print("[oshell.accent]a[/] [oshell.ok]b[/] [oshell.err]c[/] [oshell.muted]d[/]")
    assert "a b c d" in console.export_text()


@pytest.mark.parametrize("fmt", themes.EXPORT_FORMATS)
def test_every_export_format_mentions_the_background(fmt):
    p = themes.get_palette("nord")
    out = themes.export(p, fmt)
    assert p.background in out
    assert fmt == "toml" or "nord" in out  # colors.toml is nameless by design
    with pytest.raises(ValueError):
        themes.export(p, "xterm-from-1987")


def test_toml_roundtrip_is_lossless():
    p = themes.get_palette("kanagawa")
    again = themes.palette_from_dict("kanagawa", themes.parse_colors_toml(p.to_toml()))
    assert again == p  # `source` is excluded from equality


def test_write_current_and_apply_theme(tmp_path, monkeypatch):
    monkeypatch.setattr(themes, "CURRENT_DIR", str(tmp_path / "current"))
    p = themes.get_palette("ristretto")
    d = themes.write_current(p)
    assert (d / "theme").read_text().strip() == "ristretto"
    for f in ("ghostty.conf", "alacritty.toml", "kitty.conf", "wezterm.lua", "colors.sh"):
        assert (d / f).is_file()
    assert 'OSHELL_ACCENT="' + p.accent + '"' in (d / "colors.sh").read_text()
    assert themes.current_name() == "ristretto"

    # apply_theme persists to config.local.json (cwd is a tmp dir via conftest)
    # and regenerates the exports.
    got = themes.apply_theme("osaka-jade")
    assert got.name == "osaka-jade"
    assert (d / "theme").read_text().strip() == "osaka-jade"
    import json

    assert json.loads(Path("config.local.json").read_text())["theme"] == "osaka-jade"
    with pytest.raises(ValueError, match="unknown theme"):
        themes.apply_theme("not-a-theme-anyone-has")


def test_import_theme_from_dir_and_file(tmp_path, monkeypatch):
    user = tmp_path / "user-themes"
    src = tmp_path / "omarchy-sunset"
    src.mkdir()
    (src / "colors.toml").write_text(
        'accent = "#ff8800"\nbackground = "#101010"\nforeground = "#f0f0f0"\n'
    )
    p = themes.import_theme(str(src), directory=user)
    assert p.name == "omarchy-sunset" and (user / "omarchy-sunset.toml").is_file()
    q = themes.import_theme(str(src / "colors.toml"), name="Sun Set!", directory=user)
    assert q.name == "sun-set"
    assert themes.get_palette("sun-set", user).accent == "#ff8800"
    with pytest.raises(FileNotFoundError):
        themes.import_theme(str(tmp_path / "nowhere"), directory=user)


def test_swatch_is_a_row_of_blocks():
    t = themes.swatch(themes.get_palette("hackerman"))
    assert set(t.plain) == {"█"}
