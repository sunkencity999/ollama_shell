"""Ambient visual effects — calm, semantic, peripheral.

The design rule: motion never lives inside text the user is reading. It lives
in the periphery (the live status strip), or on a dedicated screen (the dream).
Every effect *means* something the app is doing:

- aurora  — the thinking status slowly drifts through cool hues (breathing)
- embers  — a spark fades in the live bar when a tool finishes (soft feedback)
- fireflies — after minutes of idleness, faint glyphs drift in the empty strip
- starfield — /daydream takes the whole stage: twinkling sky + streaming dream

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
class StarfieldModel:
    """A twinkling sky with the occasional comet, plus a centered dream text.

    Pure state + a Text renderer — no Textual imports, fully testable.
    """

    n_stars: int = 90
    seed: int | None = None
    stars: list[_Star] = field(default_factory=list)
    comet: _Comet | None = None
    tick: int = 0

    def __post_init__(self) -> None:
        rng = random.Random(self.seed)
        self._rng = rng
        self.stars = [
            _Star(
                x=rng.random(),
                y=rng.random(),
                phase=rng.random() * math.tau,
                speed=0.08 + rng.random() * 0.22,
            )
            for _ in range(self.n_stars)
        ]

    def step(self) -> None:
        """Advance one animation frame (twinkle; maybe birth/move a comet)."""
        self.tick += 1
        for s in self.stars:
            s.phase += s.speed
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
