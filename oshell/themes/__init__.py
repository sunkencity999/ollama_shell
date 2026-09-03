"""Themes — one palette, every surface (the Omarchy idea, for a shell).

Omarchy's trick is that a theme is just a small ``colors.toml`` and *one*
command restyles the whole desktop. We borrow the format wholesale, so the
22 palettes Omarchy ships live here as bundled data and any of the hundreds
of community Omarchy themes drops straight in::

    oshell theme list                       # bundled + ~/.oshell/themes/*.toml
    oshell theme set osaka-jade             # TUI + CLI + ~/.oshell/current/*
    oshell theme import ~/omarchy-foo       # a dir with colors.toml, or a URL
    oshell theme export ghostty >> ~/.config/ghostty/config

A palette becomes, on demand:

* a Textual ``Theme`` (the TUI workspace, registered at startup),
* a Rich ``Theme`` (the plain CLI: prompts, panels, tool lines),
* terminal color configs (Ghostty, Alacritty, Kitty, WezTerm) and a
  ``colors.sh`` you can source from a prompt — all regenerated into
  ``~/.oshell/current/`` whenever the theme changes, Omarchy's
  ``~/.config/omarchy/current`` pattern.

Textual's own built-in themes (``textual-dark``, ``dracula``, …) still work
as ``theme`` values; they just don't carry a palette for the other surfaces.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

PALETTE_DIR = Path(__file__).parent / "palettes"
USER_DIR = "~/.oshell/themes"
CURRENT_DIR = "~/.oshell/current"
DEFAULT_THEME = "tokyo-night"

# Keys a colors.toml may carry. Only the first block is required; the rest
# have sensible fallbacks so a minimal community theme still loads.
_REQUIRED = ("accent", "background", "foreground")
_COLOR_KEYS = (
    "accent",
    "selection",
    "muted",
    "background",
    "dark_background",
    "darker_background",
    "lighter_background",
    "foreground",
    "dark_foreground",
    "light_foreground",
    "bright_foreground",
    "red",
    "yellow",
    "orange",
    "green",
    "cyan",
    "blue",
    "magenta",
    "brown",
    "bright_red",
    "bright_yellow",
    "bright_green",
    "bright_cyan",
    "bright_blue",
    "bright_magenta",
)
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


@dataclass(frozen=True)
class Palette:
    """One theme's colors, normalized (every field a ``#rrggbb`` string)."""

    name: str
    mode: str = "dark"
    accent: str = "#7aa2f7"
    selection: str = "#292e42"
    muted: str = "#414868"
    background: str = "#1a1b26"
    dark_background: str = "#13141c"
    darker_background: str = "#0e0e14"
    lighter_background: str = "#24283b"
    foreground: str = "#a9b1d6"
    dark_foreground: str = "#565f89"
    light_foreground: str = "#b4bee6"
    bright_foreground: str = "#c0caf5"
    red: str = "#f7768e"
    yellow: str = "#e0af68"
    orange: str = "#eb927b"
    green: str = "#9ece6a"
    cyan: str = "#449dab"
    blue: str = "#7aa2f7"
    magenta: str = "#ad8ee6"
    brown: str = "#75493d"
    bright_red: str = "#ff7a93"
    bright_yellow: str = "#ff9e64"
    bright_green: str = "#b9f27c"
    bright_cyan: str = "#0db9d7"
    bright_blue: str = "#7da6ff"
    bright_magenta: str = "#bb9af7"
    source: str = field(default="builtin", compare=False)

    @property
    def dark(self) -> bool:
        return self.mode != "light"

    # 16-color ANSI table, in the order terminals expect (0..15).
    def ansi(self) -> list[str]:
        return [
            self.muted,
            self.red,
            self.green,
            self.yellow,
            self.blue,
            self.magenta,
            self.cyan,
            self.foreground,
            self.dark_foreground,
            self.bright_red,
            self.bright_green,
            self.bright_yellow,
            self.bright_blue,
            self.bright_magenta,
            self.bright_cyan,
            self.bright_foreground,
        ]

    def to_toml(self) -> str:
        """Round-trip back to Omarchy's colors.toml shape."""
        lines = [f'mode = "{self.mode}"', ""]
        for key in _COLOR_KEYS:
            lines.append(f'{key} = "{getattr(self, key)}"')
            if key in ("muted", "lighter_background", "bright_foreground", "brown"):
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"


# ── parsing ──────────────────────────────────────────────────────────────────
def parse_colors_toml(text: str) -> dict[str, str]:
    """Parse the flat ``key = "value"`` TOML Omarchy uses.

    Uses the stdlib parser on 3.11+, and a tiny line parser otherwise (the
    format is deliberately trivial: no tables, no arrays). Non-string values
    are dropped — only colors and ``mode`` matter here.
    """
    data: dict[str, Any]
    try:
        import tomllib  # Python 3.11+
    except ImportError:  # pragma: no cover - 3.10 only
        tomllib = None  # type: ignore[assignment]
    if tomllib is not None:
        try:
            data = tomllib.loads(text)
        except Exception as exc:  # malformed TOML
            raise ValueError(f"not a colors.toml: {exc}") from exc
    else:  # pragma: no cover - 3.10 only
        data = {}
        line_re = re.compile(r'^\s*([A-Za-z_][\w]*)\s*=\s*"([^"]*)"\s*(#.*)?$')
        for raw in text.splitlines():
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            m = line_re.match(raw)
            if not m:
                raise ValueError(f"not a colors.toml: can't parse line {raw.strip()!r}")
            data[m.group(1)] = m.group(2)
    return {k: v for k, v in data.items() if isinstance(v, str)}


def palette_from_dict(name: str, data: dict[str, str], source: str = "file") -> Palette:
    """Build a Palette, filling gaps the way a terminal would guess them."""
    missing = [k for k in _REQUIRED if k not in data]
    if missing:
        raise ValueError(f"theme '{name}' is missing required colors: {', '.join(missing)}")
    d = dict(data)
    mode = d.get("mode", "dark").lower()
    mode = "light" if mode == "light" else "dark"
    bg, fg = d["background"], d["foreground"]
    # Backgrounds: derive the ladder from the base if a theme skipped rungs.
    d.setdefault("dark_background", _shade(bg, -0.05 if mode == "dark" else 0.04))
    d.setdefault("darker_background", _shade(bg, -0.10 if mode == "dark" else 0.08))
    d.setdefault("lighter_background", _shade(bg, 0.08 if mode == "dark" else -0.08))
    d.setdefault("selection", d["lighter_background"])
    d.setdefault("muted", _mix(bg, fg, 0.35))
    d.setdefault("dark_foreground", _mix(bg, fg, 0.55))
    d.setdefault("light_foreground", _mix(fg, "#ffffff" if mode == "dark" else "#000000", 0.15))
    d.setdefault("bright_foreground", _mix(fg, "#ffffff" if mode == "dark" else "#000000", 0.3))
    # Chromatic colors: fall back sideways to the nearest sibling.
    accent = d["accent"]
    d.setdefault("blue", accent)
    d.setdefault("red", "#f7768e")
    d.setdefault("green", "#9ece6a")
    d.setdefault("yellow", "#e0af68")
    d.setdefault("cyan", d["blue"])
    d.setdefault("magenta", accent)
    d.setdefault("orange", d["yellow"])
    d.setdefault("brown", d["muted"])
    for k in ("red", "yellow", "green", "cyan", "blue", "magenta"):
        d.setdefault(f"bright_{k}", d[k])
    kwargs: dict[str, str] = {}
    for key in _COLOR_KEYS:
        value = d[key].strip()
        if not _HEX_RE.match(value):
            raise ValueError(f"theme '{name}': {key} = {value!r} is not a #rrggbb color")
        kwargs[key] = value.lower()
    return Palette(name=name, mode=mode, source=source, **kwargs)


def load_palette_file(
    path: Path | str, name: str | None = None, source: str | None = None
) -> Palette:
    """Load a Palette from a colors.toml (or a dir containing one)."""
    p = Path(path).expanduser()
    if p.is_dir():
        p = p / "colors.toml"
    if not p.is_file():
        raise FileNotFoundError(f"no colors.toml at {p}")
    data = parse_colors_toml(p.read_text(encoding="utf-8"))
    theme_name = name or (p.parent.name if p.name == "colors.toml" else p.stem)
    return palette_from_dict(_slug(theme_name), data, source=source or str(p))


# ── registry: bundled + user ─────────────────────────────────────────────────
def user_dir(directory: str | Path | None = None) -> Path:
    # Looked up at call time so tests (and adventurous users) can repoint it.
    return Path(directory or USER_DIR).expanduser()


def builtin_names() -> list[str]:
    return sorted(p.stem for p in PALETTE_DIR.glob("*.toml"))


def list_palettes(directory: str | Path | None = None) -> dict[str, Palette]:
    """name -> Palette for every bundled and user theme (user wins on clash)."""
    out: dict[str, Palette] = {}
    for f in sorted(PALETTE_DIR.glob("*.toml")):
        try:
            out[f.stem] = load_palette_file(f, f.stem, source="builtin")
        except (ValueError, OSError):  # pragma: no cover - bundled data is vetted
            continue
    d = user_dir(directory)
    if d.is_dir():
        for f in sorted(d.glob("*.toml")):
            try:
                out[f.stem] = load_palette_file(f, f.stem)
            except (ValueError, OSError):
                continue  # a broken user theme must never break startup
        for sub in sorted(x for x in d.iterdir() if x.is_dir()):
            if (sub / "colors.toml").is_file():
                try:
                    out[sub.name] = load_palette_file(sub, sub.name)
                except (ValueError, OSError):
                    continue
    return out


def get_palette(name: str, directory: str | Path | None = None) -> Palette | None:
    """The named palette, or None (e.g. a Textual built-in like 'dracula')."""
    slug = _slug(name)
    d = user_dir(directory)
    for candidate in (d / f"{slug}.toml", d / slug / "colors.toml", PALETTE_DIR / f"{slug}.toml"):
        if candidate.is_file():
            try:
                return load_palette_file(
                    candidate, slug, source="builtin" if candidate.parent == PALETTE_DIR else None
                )
            except ValueError:
                return None
    return None


def import_theme(src: str, name: str | None = None, directory: str | Path | None = None) -> Palette:
    """Copy a theme into ~/.oshell/themes from a file, a directory, or a URL.

    URLs: a raw ``colors.toml`` link, or a GitHub repo/tree URL for an Omarchy
    theme (``https://github.com/user/repo`` → tries ``colors.toml`` on the
    default branches). Nothing is fetched unless you asked for a URL — this is
    the one place the theme system touches the network.
    """
    if src.startswith(("http://", "https://")):
        text, guessed = _fetch_theme_text(src)
        palette = palette_from_dict(_slug(name or guessed), parse_colors_toml(text), source=src)
    else:
        palette = load_palette_file(src, name)
        if name:
            palette = Palette(**{**_asdict(palette), "name": _slug(name)})
    d = user_dir(directory)
    d.mkdir(parents=True, exist_ok=True)
    target = d / f"{palette.name}.toml"
    target.write_text(palette.to_toml(), encoding="utf-8")
    return Palette(**{**_asdict(palette), "source": str(target)})


def _fetch_theme_text(url: str) -> tuple[str, str]:
    import requests

    candidates: list[str] = []
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if m:
        user, repo = m.groups()
        for branch in ("main", "master"):
            candidates.append(
                f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/colors.toml"
            )
        guessed = repo.removeprefix("omarchy-").removesuffix("-theme")
    else:
        tree = re.match(r"https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)$", url)
        if tree:
            user, repo, branch, path = tree.groups()
            candidates.append(
                f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path.rstrip('/')}/colors.toml"
            )
            guessed = path.rstrip("/").rsplit("/", 1)[-1]
        else:
            candidates.append(url)
            tail = url.rstrip("/").rsplit("/", 1)[-1]
            guessed = tail if tail != "colors.toml" else url.rstrip("/").rsplit("/", 2)[-2]
    last_err = "no candidates"
    for cand in candidates:
        try:
            r = requests.get(cand, timeout=15)
            if r.ok and "=" in r.text:
                return r.text, guessed
            last_err = f"{cand} → HTTP {r.status_code}"
        except requests.RequestException as exc:
            last_err = str(exc)
    raise ValueError(f"could not fetch a colors.toml from {url} ({last_err})")


# ── adapters ─────────────────────────────────────────────────────────────────
def to_textual_theme(p: Palette):
    """A Textual ``Theme`` built from the palette (import is lazy: [tui] extra)."""
    from textual.theme import Theme

    # A second hue for "secondary" so it doesn't collapse into the accent.
    secondary = p.magenta if _close(p.blue, p.accent) else p.blue
    if _close(secondary, p.accent):
        secondary = p.cyan
    pop = p.orange if not _close(p.orange, p.yellow) else p.bright_yellow
    if _close(pop, p.accent):
        pop = p.bright_magenta
    surface = p.lighter_background if p.dark else p.dark_background
    panel = p.selection if not _close(p.selection, surface) else p.muted
    return Theme(
        name=p.name,
        primary=p.accent,
        secondary=secondary,
        accent=pop,
        warning=p.yellow,
        error=p.red,
        success=p.green,
        foreground=p.foreground,
        background=p.background,
        surface=surface,
        panel=panel,
        dark=p.dark,
        variables={
            "border": p.accent,
            "border-blurred": p.muted,
            "footer-key-foreground": p.accent,
            "footer-background": p.dark_background,
            "footer-description-foreground": p.dark_foreground,
            "block-cursor-background": p.accent,
            "block-cursor-foreground": p.background,
            "input-selection-background": p.selection,
            "input-cursor-background": p.accent,
            "input-cursor-foreground": p.background,
            "button-color-foreground": p.background,
            "link-color": p.bright_blue,
            "link-color-hover": p.bright_cyan,
            "scrollbar": p.muted,
            "scrollbar-hover": p.dark_foreground,
            "scrollbar-active": p.accent,
            "scrollbar-background": p.background,
        },
    )


def to_rich_theme(p: Palette):
    """A Rich ``Theme`` of semantic styles the CLI uses (``oshell.*``)."""
    from rich.theme import Theme

    return Theme(
        {
            "oshell.accent": f"bold {p.accent}",
            "oshell.title": f"bold {p.bright_foreground}",
            "oshell.muted": p.dark_foreground,
            "oshell.border": p.accent,
            "oshell.border.soft": p.muted,
            "oshell.ok": p.green,
            "oshell.warn": p.yellow,
            "oshell.err": p.red,
            "oshell.tool": f"{p.magenta}",
            "oshell.prompt": f"bold {p.accent}",
            "oshell.cmd": f"bold {p.bright_foreground}",
            "oshell.net": p.orange,
            "oshell.local": p.green,
            "oshell.exec": p.red,
            # Nudge a few of Rich's defaults toward the palette.
            "markdown.code": f"bold {p.cyan}",
            "markdown.link": p.bright_blue,
            "markdown.h1": f"bold {p.accent}",
            "markdown.h2": f"bold {p.blue}",
            "rule.line": p.muted,
            "prompt.choices": p.accent,
            "prompt.default": p.dark_foreground,
        }
    )


def swatch(p: Palette, width: int = 8):
    """A row of colored blocks previewing the palette (Rich Text)."""
    from rich.text import Text

    t = Text()
    t.append("██", style=p.background)
    for c in (p.accent, p.red, p.yellow, p.green, p.cyan, p.blue, p.magenta):
        t.append("█", style=c)
    t.append("█", style=p.foreground)
    return t


# ── exports for terminals & shells ───────────────────────────────────────────
EXPORT_FORMATS = (
    "ghostty",
    "alacritty",
    "kitty",
    "wezterm",
    "windows-terminal",
    "sh",
    "toml",
    "btop",
)


def export(p: Palette, fmt: str) -> str:
    """Render the palette as a config snippet for ``fmt`` (see EXPORT_FORMATS)."""
    a = p.ansi()
    if fmt == "toml":
        return p.to_toml()
    if fmt == "sh":
        lines = [f"# oshell theme: {p.name} ({p.mode}) — source me", f'OSHELL_THEME="{p.name}"']
        for key in _COLOR_KEYS:
            lines.append(f'OSHELL_{key.upper()}="{getattr(p, key)}"')
        lines.append(f'OSHELL_MODE="{p.mode}"')
        return "\n".join(lines) + "\n"
    if fmt == "ghostty":
        lines = [f"# oshell theme: {p.name}"]
        lines += [f"palette = {i}={c}" for i, c in enumerate(a)]
        lines += [
            f"background = {p.background}",
            f"foreground = {p.foreground}",
            f"cursor-color = {p.accent}",
            f"cursor-text = {p.background}",
            f"selection-background = {p.selection}",
            f"selection-foreground = {p.bright_foreground}",
        ]
        return "\n".join(lines) + "\n"
    if fmt == "alacritty":
        names = ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")
        out = [
            f"# oshell theme: {p.name}",
            "[colors.primary]",
            f'background = "{p.background}"',
            f'foreground = "{p.foreground}"',
            f'dim_foreground = "{p.dark_foreground}"',
            f'bright_foreground = "{p.bright_foreground}"',
            "",
            "[colors.cursor]",
            f'text = "{p.background}"',
            f'cursor = "{p.accent}"',
            "",
            "[colors.selection]",
            f'text = "{p.bright_foreground}"',
            f'background = "{p.selection}"',
            "",
            "[colors.normal]",
        ]
        out += [f'{n} = "{a[i]}"' for i, n in enumerate(names)]
        out += ["", "[colors.bright]"]
        out += [f'{n} = "{a[8 + i]}"' for i, n in enumerate(names)]
        return "\n".join(out) + "\n"
    if fmt == "kitty":
        out = [
            f"# oshell theme: {p.name}",
            f"foreground {p.foreground}",
            f"background {p.background}",
            f"selection_foreground {p.bright_foreground}",
            f"selection_background {p.selection}",
            f"cursor {p.accent}",
            f"cursor_text_color {p.background}",
            f"url_color {p.bright_blue}",
            f"active_border_color {p.accent}",
            f"inactive_border_color {p.muted}",
            f"active_tab_background {p.accent}",
            f"active_tab_foreground {p.background}",
            f"inactive_tab_background {p.dark_background}",
            f"inactive_tab_foreground {p.dark_foreground}",
        ]
        out += [f"color{i} {c}" for i, c in enumerate(a)]
        return "\n".join(out) + "\n"
    if fmt == "wezterm":
        ansi = ", ".join(f'"{c}"' for c in a[:8])
        brights = ", ".join(f'"{c}"' for c in a[8:])
        return (
            f"-- oshell theme: {p.name}\n"
            "return {\n"
            f'  foreground = "{p.foreground}",\n'
            f'  background = "{p.background}",\n'
            f'  cursor_bg = "{p.accent}",\n'
            f'  cursor_fg = "{p.background}",\n'
            f'  cursor_border = "{p.accent}",\n'
            f'  selection_bg = "{p.selection}",\n'
            f'  selection_fg = "{p.bright_foreground}",\n'
            f"  ansi = {{ {ansi} }},\n"
            f"  brights = {{ {brights} }},\n"
            "}\n"
        )
    if fmt == "windows-terminal":
        # A color scheme object for settings.json → "schemes": [ … ]; then set
        # "colorScheme": "oshell-<name>" on a profile.
        import json

        names = ("black", "red", "green", "yellow", "blue", "purple", "cyan", "white")
        scheme = {
            "name": f"oshell-{p.name}",
            "background": p.background,
            "foreground": p.foreground,
            "cursorColor": p.accent,
            "selectionBackground": p.selection,
        }
        for i, n in enumerate(names):
            scheme[n] = a[i]
            scheme["bright" + n.capitalize()] = a[8 + i]
        return json.dumps(scheme, indent=2) + "\n"
    if fmt == "btop":
        # btop's theme format: theme[key]="#hex". Enough keys to feel native.
        keys = {
            "main_bg": p.background,
            "main_fg": p.foreground,
            "title": p.bright_foreground,
            "hi_fg": p.accent,
            "selected_bg": p.selection,
            "selected_fg": p.bright_foreground,
            "inactive_fg": p.dark_foreground,
            "graph_text": p.foreground,
            "meter_bg": p.muted,
            "proc_misc": p.cyan,
            "cpu_box": p.accent,
            "mem_box": p.green,
            "net_box": p.magenta,
            "proc_box": p.blue,
            "div_line": p.muted,
            "temp_start": p.green,
            "temp_mid": p.yellow,
            "temp_end": p.red,
            "cpu_start": p.green,
            "cpu_mid": p.yellow,
            "cpu_end": p.red,
            "free_start": p.green,
            "free_mid": p.green,
            "free_end": p.green,
            "cached_start": p.cyan,
            "cached_mid": p.cyan,
            "cached_end": p.cyan,
            "available_start": p.yellow,
            "available_mid": p.yellow,
            "available_end": p.yellow,
            "used_start": p.red,
            "used_mid": p.red,
            "used_end": p.red,
            "download_start": p.blue,
            "download_mid": p.blue,
            "download_end": p.bright_blue,
            "upload_start": p.magenta,
            "upload_mid": p.magenta,
            "upload_end": p.bright_magenta,
        }
        return (
            f"# oshell theme: {p.name}\n"
            + "\n".join(f'theme[{k}]="{v}"' for k, v in keys.items())
            + "\n"
        )
    raise ValueError(f"unknown export format {fmt!r} (try: {', '.join(EXPORT_FORMATS)})")


_CURRENT_FILES = {
    "theme.toml": "toml",
    "colors.sh": "sh",
    "ghostty.conf": "ghostty",
    "alacritty.toml": "alacritty",
    "kitty.conf": "kitty",
    "wezterm.lua": "wezterm",
    "windows-terminal.json": "windows-terminal",
    "btop.theme": "btop",
}


def current_dir(directory: str | Path | None = None) -> Path:
    return Path(directory or CURRENT_DIR).expanduser()


def write_current(p: Palette, directory: str | Path | None = None) -> Path:
    """Regenerate ~/.oshell/current/* for the palette (every export + name)."""
    d = current_dir(directory)
    d.mkdir(parents=True, exist_ok=True)
    for fname, fmt in _CURRENT_FILES.items():
        (d / fname).write_text(export(p, fmt), encoding="utf-8")
    (d / "theme").write_text(p.name + "\n", encoding="utf-8")
    return d


def current_name(directory: str | Path | None = None) -> str | None:
    f = current_dir(directory) / "theme"
    try:
        return f.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def apply_theme(name: str, root: Path | str | None = None) -> Palette | None:
    """Make ``name`` the theme: persist to config.local.json, refresh current/.

    Returns the Palette (None if ``name`` is a Textual built-in, which is still
    persisted — it just has nothing to export).
    """
    from ..config import update_local_config

    palette = get_palette(name)
    if palette is None:
        try:
            from textual.theme import BUILTIN_THEMES

            known = set(BUILTIN_THEMES)
        except ImportError:  # no [tui]: can't verify Textual names, be lenient
            known = {name}
        if name not in known:
            raise ValueError(f"unknown theme: {name} (see: oshell theme list)")
    update_local_config({"theme": name}, root=root)
    if palette is not None:
        write_current(palette)
    return palette


# ── color math (no deps) ─────────────────────────────────────────────────────
def _rgb(hexstr: str) -> tuple[int, int, int]:
    h = hexstr.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def _mix(a: str, b: str, t: float) -> str:
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(x + (y - x) * t for x, y in zip(ra, rb, strict=True)))


def _shade(color: str, amount: float) -> str:
    """Lighten (amount>0) or darken (amount<0) toward white/black."""
    return _mix(color, "#ffffff" if amount > 0 else "#000000", abs(amount))


def _close(a: str, b: str, tol: int = 24) -> bool:
    return all(abs(x - y) <= tol for x, y in zip(_rgb(a), _rgb(b), strict=True))


def luminance(color: str) -> float:
    r, g, b = (c / 255 for c in _rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "theme"


def _asdict(p: Palette) -> dict[str, Any]:
    return {f.name: getattr(p, f.name) for f in fields(p)}
