"""Ambient visual effects — calm, semantic, peripheral.

The design rule: motion never lives inside text the user is reading. It lives
in the periphery (the live status strip), or on a dedicated screen (the dream).
Every effect *means* something the app is doing:

- aurora  — the thinking status slowly drifts through cool hues (breathing)
- embers  — a spark fades in the live bar when a tool finishes (soft feedback)
- fireflies — after minutes of idleness, faint glyphs drift in the empty strip
- starfield — /daydream takes the whole stage: twinkling sky + streaming dream
- weather — the dream sky takes a mood: rain after a stormy debugging session,
  snow in December, clear otherwise
- burst — a brief scatter of warm sparks when the model hits the tool cap
- constellation — a few faint stars behind the startup menu

Everything here is pure model + string/Text builders so it's unit-testable;
the widgets/screens that drive them are thin.
"""

from __future__ import annotations

import math
import random
import textwrap
from dataclasses import dataclass, field

from rich.text import Text

# ── aurora: a slow drift of cool hues for the thinking status ────────────────
AURORA = [
    "#4fd1c5",
    "#55c6d3",
    "#63b8e2",
    "#7aa8ee",
    "#9398f4",
    "#a98cf2",
    "#bd85e9",
    "#c78be6",
    "#b591ea",
    "#9aa0f0",
    "#7fb2ec",
    "#63c2de",
]


def aurora_color(phase: int) -> str:
    """The hue for this animation phase; cycles slowly (callers pass a tick/3)."""
    return AURORA[phase % len(AURORA)]


# ── embers: a one-second spark when a tool finishes ──────────────────────────
EMBER_FRAMES = ["✦", "✧", "∗", "·"]
EMBER_SECONDS = 1.2  # how long a spark lives

# Palette by what *kind* of thing finished — net=amber, memory=magenta, local=green.
EMBER_COLORS = {"net": "#e7c667", "memory": "#c78be6", "local": "#7bd88f"}

_NET_HINTS = ("web_", "fetch", "browser_", "jira_", "confluence_")
_MEMORY_HINTS = ("remember", "forget", "recall")


def ember_color_for(tool_name: str) -> str:
    """Pick the spark colour from the tool's nature."""
    if any(tool_name.startswith(h) or tool_name == h for h in _MEMORY_HINTS):
        return EMBER_COLORS["memory"]
    if any(tool_name.startswith(h) for h in _NET_HINTS):
        return EMBER_COLORS["net"]
    return EMBER_COLORS["local"]


def ember_glyph(age_seconds: float) -> str | None:
    """The spark's glyph for its age, or None once it has burned out."""
    if age_seconds < 0 or age_seconds >= EMBER_SECONDS:
        return None
    i = int(age_seconds / EMBER_SECONDS * len(EMBER_FRAMES))
    return EMBER_FRAMES[min(i, len(EMBER_FRAMES) - 1)]


# ── fireflies: company for an idle shell ─────────────────────────────────────
IDLE_FIREFLIES_AFTER = 120.0  # seconds of quiet before they appear

_FLY_GLYPHS = ["✦", "·", "✧"]
_FLY_STYLES = ["#e7c667", "#b8cc7a", "#7bd88f"]


def fireflies_markup(width: int, tick: int) -> str:
    """A single line of 3 faint fireflies drifting on sine paths.

    Deterministic in (width, tick) so it can be tested; callers advance ``tick``.
    """
    width = max(width, 16)
    row = [" "] * width
    marks: dict[int, tuple[str, str]] = {}
    for i in range(3):
        # Each fly has its own speed, phase and wander-width.
        x = int((width / 2) + (width / 2 - 4) * math.sin(tick * (0.05 + i * 0.021) + i * 2.1))
        x = min(max(x, 0), width - 1)
        pulse = _FLY_GLYPHS[(tick // (3 + i)) % len(_FLY_GLYPHS)]
        marks[x] = (pulse, _FLY_STYLES[i])
    out = []
    for x in range(width):
        if x in marks:
            ch, style = marks[x]
            out.append(f"[dim {style}]{ch}[/]")
        else:
            out.append(row[x])
    return "".join(out).rstrip()


# ── burst: a particle storm when the tool-iteration cap is hit ───────────────
BURST_SECONDS = 1.6  # how long the scatter lasts

_BURST_GLYPHS = ["✷", "✶", "✧", "∗", "·"]
_BURST_COLORS = ["#e7c667", "#e78a5a", "#d96f6f"]


def burst_markup(width: int, age_seconds: float, seed: int = 7) -> str | None:
    """One line of scattering sparks, thinning as they age; None once spent.

    Deterministic in (width, seed, frame) — the frame is the age quantized to
    10fps — so tests can pin any moment of the storm.
    """
    if age_seconds < 0 or age_seconds >= BURST_SECONDS:
        return None
    width = max(width, 16)
    frame = int(age_seconds * 10)
    rng = random.Random(seed * 1000 + frame)
    fade = 1.0 - age_seconds / BURST_SECONDS
    n = max(2, int(12 * fade))
    marks: dict[int, tuple[str, str]] = {}
    for _ in range(n):
        x = rng.randrange(width)
        glyph = _BURST_GLYPHS[min(int((1 - fade) * len(_BURST_GLYPHS)), len(_BURST_GLYPHS) - 1)]
        marks[x] = (glyph, rng.choice(_BURST_COLORS))
    out = []
    for x in range(width):
        if x in marks:
            ch, color = marks[x]
            out.append(f"[{color}]{ch}[/]")
        else:
            out.append(" ")
    return "".join(out).rstrip()


# ── constellation: a few faint stars behind the startup menu ─────────────────
_CONST_GLYPHS = ["·", "✧", "·", "✦", "·"]


def constellation_line(width: int, seed: int = 3) -> str:
    """A static line of faint, well-spaced stars (markup). Deterministic."""
    width = max(width, 16)
    rng = random.Random(seed)
    n = max(3, width // 12)
    xs = sorted(rng.sample(range(width), min(n, width)))
    marks = {x: _CONST_GLYPHS[rng.randrange(len(_CONST_GLYPHS))] for x in xs}
    out = []
    for x in range(width):
        out.append(f"[dim #6b7f9e]{marks[x]}[/]" if x in marks else " ")
    return "".join(out).rstrip()


# ── weather: the dream sky takes a mood from the session ─────────────────────
# Words that mark a stormy stretch of conversation (debugging in the rain).
_STORM_WORDS = (
    "error",
    "exception",
    "traceback",
    "crash",
    "fail",
    "failure",
    "broken",
    "bug",
    "debug",
    "segfault",
    "panic",
    "stack trace",
)


def sky_mood(topics: list[str], month: int) -> str:
    """Pick the dream sky's weather: "rain" | "snow" | "clear".

    Rain after a stormy debugging session (two or more storm words in the
    recent topics), snow in December, otherwise a clear night.
    """
    text = " ".join(topics).lower()
    hits = sum(text.count(w) for w in _STORM_WORDS)
    if hits >= 2:
        return "rain"
    if month == 12:
        return "snow"
    return "clear"


# ── the starfield: /daydream's night sky ─────────────────────────────────────
_STAR_CHARS = ["·", "✧", "✦", "*"]
_STAR_STYLES = ["dim #6b7f9e", "#8fa8d8", "#cfe3ff", "bold #ffffff"]


@dataclass
class _Star:
    x: float  # fraction of width  (0..1)
    y: float  # fraction of height (0..1)
    phase: float  # twinkle position
    speed: float  # twinkle speed


@dataclass
class _Comet:
    x: float
    y: float
    dx: float
    dy: float
    life: int


@dataclass
class _Flake:
    """One falling particle of weather (a raindrop or a snowflake)."""

    x: float
    y: float
    speed: float
    sway: float  # phase for snow's sideways drift


# Weather particle looks: rain streaks steel-blue, snow drifts white.
_RAIN_GLYPH, _RAIN_STYLE = "╱", "dim #6fa8dc"
_SNOW_GLYPHS = ["❄", "✻", "·"]
_SNOW_STYLE = "#dbe7f3"


@dataclass
class StarfieldModel:
    """A twinkling sky with the occasional comet, plus a centered dream text.

    Pure state + a Text renderer — no Textual imports, fully testable.
    ``weather`` ("clear" | "rain" | "snow") adds falling particles; ``density``
    scales how full the sky is (stars and weather alike).
    """

    n_stars: int = 90
    seed: int | None = None
    weather: str = "clear"
    density: float = 1.0
    stars: list[_Star] = field(default_factory=list)
    comet: _Comet | None = None
    flakes: list[_Flake] = field(default_factory=list)
    tick: int = 0

    def __post_init__(self) -> None:
        rng = random.Random(self.seed)
        self._rng = rng
        density = max(0.0, self.density)
        self.stars = [
            _Star(
                x=rng.random(),
                y=rng.random(),
                phase=rng.random() * math.tau,
                speed=0.08 + rng.random() * 0.22,
            )
            for _ in range(int(round(self.n_stars * density)))
        ]
        if self.weather in ("rain", "snow"):
            base = 26 if self.weather == "rain" else 16
            self.flakes = [
                _Flake(
                    x=rng.random(),
                    y=rng.random(),
                    speed=(0.06 + rng.random() * 0.03)
                    if self.weather == "rain"
                    else (0.012 + rng.random() * 0.01),
                    sway=rng.random() * math.tau,
                )
                for _ in range(max(3, int(round(base * density))))
            ]

    def step(self) -> None:
        """Advance one animation frame (twinkle; weather falls; maybe a comet)."""
        self.tick += 1
        for s in self.stars:
            s.phase += s.speed
        for f in self.flakes:
            f.y += f.speed
            if self.weather == "rain":
                f.x -= f.speed * 0.35  # streaks lean the way the glyph points
            else:
                f.sway += 0.08
                f.x += math.sin(f.sway) * 0.004  # lazy sideways drift
            if f.y > 1.0:  # recycle at the top, at a fresh column
                f.y = 0.0
                f.x = self._rng.random()
            f.x %= 1.0
        if self.comet is None:
            if self._rng.random() < 0.015:  # a shooting star every ~7s at 10fps
                going_right = self._rng.random() < 0.5
                self.comet = _Comet(
                    x=0.05 if going_right else 0.95,
                    y=self._rng.random() * 0.4,
                    dx=0.02 if going_right else -0.02,
                    dy=0.012,
                    life=40,
                )
        else:
            c = self.comet
            c.x += c.dx
            c.y += c.dy
            c.life -= 1
            if c.life <= 0 or not (0 <= c.x <= 1) or not (0 <= c.y <= 1):
                self.comet = None

    def render(self, width: int, height: int, dream: str = "", done: bool = False) -> Text:
        """Compose the sky + centered dream text as a Rich Text.

        Built as explicit-styled Text (never markup), so arbitrary dream
        content can't break the render — same hardening rule as the panels.
        """
        width = max(width, 20)
        height = max(height, 8)
        # Sparse star map: cell -> (char, style)
        cells: dict[tuple[int, int], tuple[str, str]] = {}
        for s in self.stars:
            cx, cy = int(s.x * (width - 1)), int(s.y * (height - 1))
            b = (math.sin(s.phase) + 1) / 2  # 0..1 brightness
            i = min(int(b * len(_STAR_CHARS)), len(_STAR_CHARS) - 1)
            cells[(cx, cy)] = (_STAR_CHARS[i], _STAR_STYLES[i])
        for i, f in enumerate(self.flakes):
            fx, fy = int(f.x * (width - 1)), int(f.y * (height - 1))
            if self.weather == "rain":
                cells[(fx, fy)] = (_RAIN_GLYPH, _RAIN_STYLE)
            else:
                cells[(fx, fy)] = (_SNOW_GLYPHS[i % len(_SNOW_GLYPHS)], _SNOW_STYLE)
        if self.comet is not None:
            c = self.comet
            cx, cy = int(c.x * (width - 1)), int(c.y * (height - 1))
            cells[(cx, cy)] = ("✺", "bold #fff7d6")
            # a short fading tail behind it
            for t in range(1, 4):
                tx = int((c.x - c.dx * t * 1.6) * (width - 1))
                ty = int((c.y - c.dy * t * 1.6) * (height - 1))
                if 0 <= tx < width and 0 <= ty < height and (tx, ty) not in cells:
                    cells[(tx, ty)] = ("·", "dim #d8cfa8")

        # The dream text block, centered.
        body_width = min(max(width - 16, 24), 72)
        lines = textwrap.wrap(dream.strip(), body_width) if dream.strip() else []
        if lines:
            lines[0] = "💭 " + lines[0]
        hint = "( press any key to wake )" if done else ""
        block_h = len(lines) + (2 if hint else 0)
        top = max((height - block_h) // 2, 1)

        text_rows: dict[int, tuple[str, str]] = {}
        for i, ln in enumerate(lines):
            text_rows[top + i] = (ln, "italic #a9b7c9")
        if hint:
            text_rows[min(top + len(lines) + 1, height - 1)] = (hint, "dim #7c8ba0")

        out = Text()
        for y in range(height):
            if y in text_rows:
                ln, style = text_rows[y]
                pad = max((width - len(ln)) // 2, 0)
                out.append(" " * pad)
                out.append(ln, style=style)
            else:
                x = 0
                row = [(cx, cells[(cx, yy)]) for (cx, yy) in cells if yy == y]
                for cx, (ch, style) in sorted(row):
                    if cx < x:
                        continue
                    out.append(" " * (cx - x))
                    out.append(ch, style=style)
                    x = cx + 1
            if y < height - 1:
                out.append("\n")
        return out
