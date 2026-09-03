"""Standing orders — outcomes you want kept true, in a text file the agent reads.

This is the whole "drive system": a Markdown list in ``~/.oshell/orders.md``
of things you care about ("keep the main disk under 80%", "tell me when a
release build lands in ~/builds", "note anything new listening on a port"),
each with a priority. One scheduled job — the ``orders`` job — wakes up
periodically, reads the list plus what it found last time, decides which
orders deserve a look *now*, checks them with read-only tools, and reports
only what changed. Anything that would change the machine is proposed, not
done (the inbox rules apply unchanged).

Why a file and not a "motivation" model: you can read it, edit it, diff it,
and the agent cannot invent work that isn't on it. Priority is the only knob:
``[high]`` orders are checked every wake, ``[normal]`` when they're due,
``[low]`` at most about once a day.

State — what was found last, and when — lives beside it in
``orders.state.json`` so the agent doesn't re-alert about the same thing.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_PATH = "~/.oshell/orders.md"
DEFAULT_STATE = "~/.oshell/orders.state.json"
PRIORITIES = ("high", "normal", "low")
STATUSES = ("ok", "attention", "skipped", "unknown")

# How stale a finding may be before an order is worth re-checking.
RECHECK_AFTER = {"high": 0, "normal": 4 * 3600, "low": 20 * 3600}

TEMPLATE = """\
# Standing orders

Outcomes you want kept true on this machine. One per line, plain language.
Tag priority with [high], [normal] (default) or [low]. Lines starting with #
are comments. The `orders` job reads this on every wake (`oshell orders`).

- [high] Keep the main disk under 80% used; warn me at 75% and say what grew.
- Tell me if anything new is listening on a network port.
- [low] Once a day, mention any launchd/systemd service that appeared or vanished.
"""

_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")
_PRIO_RE = re.compile(r"^\[(high|normal|low)\]\s*", re.I)
_STATUS_LINE_RE = re.compile(
    r"^\s*#?\s*(\d+)\s*[:.)-]?\s*(ok|attention|skipped|unknown)\b\s*[—:-]?\s*(.*)$", re.I
)


@dataclass
class Order:
    n: int  # 1-based position in the file (what the model refers to)
    text: str
    priority: str = "normal"

    @property
    def id(self) -> str:
        """Stable across reordering: a hash of the text."""
        return hashlib.sha1(self.text.strip().lower().encode("utf-8")).hexdigest()[:10]


@dataclass
class Finding:
    status: str = "unknown"
    note: str = ""
    ts: float = 0.0

    def age(self, now: float | None = None) -> float:
        return (now or time.time()) - self.ts if self.ts else float("inf")


@dataclass
class State:
    findings: dict[str, Finding] = field(default_factory=dict)  # order id → last finding
    last_run: float | None = None


# ── the orders file ──────────────────────────────────────────────────────────
def orders_path(path: str | Path | None = None) -> Path:
    return Path(path or DEFAULT_PATH).expanduser()


def state_path(path: str | Path | None = None) -> Path:
    return Path(path or DEFAULT_STATE).expanduser()


def parse_orders(text: str) -> list[Order]:
    """Bullets (``-``, ``*``, ``1.``) become orders; headings/comments/blank are ignored."""
    out: list[Order] = []
    for raw in text.splitlines():
        if raw.lstrip().startswith("#"):
            continue
        m = _BULLET_RE.match(raw)
        if not m:
            continue
        body = m.group(1)
        prio = "normal"
        pm = _PRIO_RE.match(body)
        if pm:
            prio = pm.group(1).lower()
            body = body[pm.end() :].strip()
        if body:
            out.append(Order(n=len(out) + 1, text=body, priority=prio))
    return out


def load_orders(path: str | Path | None = None) -> list[Order]:
    p = orders_path(path)
    if not p.is_file():
        return []
    try:
        return parse_orders(p.read_text(encoding="utf-8"))
    except OSError:
        return []


def ensure_file(path: str | Path | None = None) -> Path:
    """Create orders.md from the template if it doesn't exist yet."""
    p = orders_path(path)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(TEMPLATE, encoding="utf-8")
    return p


def add_order(text: str, priority: str = "normal", path: str | Path | None = None) -> Order:
    if priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {', '.join(PRIORITIES)}")
    text = " ".join(text.split())
    if not text:
        raise ValueError("an order needs text")
    p = ensure_file(path)
    body = p.read_text(encoding="utf-8")
    tag = f"[{priority}] " if priority != "normal" else ""
    body = body.rstrip("\n") + f"\n- {tag}{text}\n"
    p.write_text(body, encoding="utf-8")
    orders = parse_orders(body)
    return orders[-1]


def remove_order(n: int, path: str | Path | None = None) -> Order:
    """Delete the n-th order (1-based) from the file; returns what was removed."""
    p = orders_path(path)
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    count = 0
    for i, raw in enumerate(lines):
        if raw.lstrip().startswith("#") or not _BULLET_RE.match(raw):
            continue
        count += 1
        if count == n:
            removed = parse_orders(raw)[0]
            del lines[i]
            p.write_text("".join(lines), encoding="utf-8")
            removed.n = n
            return removed
    raise IndexError(f"no order #{n}")


# ── state ────────────────────────────────────────────────────────────────────
def load_state(path: str | Path | None = None) -> State:
    p = state_path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        findings = {k: Finding(**v) for k, v in (data.get("findings") or {}).items()}
        return State(findings=findings, last_run=data.get("last_run"))
    except (OSError, ValueError, TypeError):
        return State()


def save_state(state: State, path: str | Path | None = None) -> Path:
    p = state_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "last_run": state.last_run,
        "findings": {k: vars(v) for k, v in state.findings.items()},
    }
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p


def due_orders(orders: list[Order], state: State, now: float | None = None) -> list[Order]:
    """Orders worth checking now: high always; others when their finding is stale
    or was 'attention'/'unknown'."""
    now = now or time.time()
    out = []
    for o in orders:
        f = state.findings.get(o.id)
        if o.priority == "high" or f is None or f.status in ("attention", "unknown"):
            out.append(o)
        elif f.age(now) >= RECHECK_AFTER[o.priority]:
            out.append(o)
    return out


# ── the prompt and the report ────────────────────────────────────────────────
PROMPT_HEAD = """\
## Standing orders
These are the user's standing orders — outcomes they want kept true on this machine. \
You are the one who keeps them. For each order marked DUE, check it now with read-only \
tools (Mechanic/Drift first when they fit, then shell inspection). Orders not marked DUE \
may be skipped unless something you see suggests otherwise.
Report only what matters: lead with anything needing attention, then one line per checked \
order. Do not repeat a finding you already reported unless it changed. If an order calls \
for an action that changes the machine, propose it — it will be queued for approval. \
Known noise to ignore: Spotlight's com.apple.mdworker services flap on every snapshot.

Orders:
{orders}

Finish with a STATUS block — one line per order, exactly this shape — so your findings \
carry to the next wake:
STATUS:
#1 ok — one-line finding
#2 attention — what needs the user
#3 skipped — not due
"""


def _fmt_age(secs: float) -> str:
    if secs == float("inf"):
        return "never"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


def build_prompt(orders: list[Order], state: State, now: float | None = None) -> str:
    now = now or time.time()
    due = {o.id for o in due_orders(orders, state, now)}
    lines = []
    for o in orders:
        f = state.findings.get(o.id)
        last = (
            f"last: {f.status} {_fmt_age(f.age(now))}" + (f' — "{f.note}"' if f.note else "")
            if f
            else "last: never checked"
        )
        flag = "  ← DUE" if o.id in due else ""
        lines.append(f"{o.n}. [{o.priority}] {o.text}  ({last}){flag}")
    return PROMPT_HEAD.format(orders="\n".join(lines))


def parse_status(report: str) -> dict[int, tuple[str, str]]:
    """The STATUS block → {order number: (status, note)}. Tolerant of sloppy shapes."""
    out: dict[int, tuple[str, str]] = {}
    lines = report.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip().upper().startswith("STATUS")), None)
    body = lines[start + 1 :] if start is not None else lines
    for ln in body:
        m = _STATUS_LINE_RE.match(ln.strip().lstrip("-*• "))
        if m:
            n, status, note = int(m.group(1)), m.group(2).lower(), m.group(3).strip()
            out[n] = (status, re.sub(r"[*_`]+", "", note)[:160])
    return out


def apply_report(orders: list[Order], state: State, report: str, now: float | None = None) -> State:
    """Fold the report's STATUS block into state (unknown orders keep their finding)."""
    now = now or time.time()
    parsed = parse_status(report)
    by_n = {o.n: o for o in orders}
    for n, (status, note) in parsed.items():
        o = by_n.get(n)
        if o is None or status == "skipped":
            continue
        state.findings[o.id] = Finding(status=status, note=note, ts=now)
    # Forget findings for orders that no longer exist.
    live = {o.id for o in orders}
    state.findings = {k: v for k, v in state.findings.items() if k in live}
    state.last_run = now
    return state


def strip_status_block(report: str) -> str:
    """The report without its STATUS trailer — and without stray status lines the
    model sometimes echoes above it (the note shows findings its own way)."""
    lines = report.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip().upper().startswith("STATUS")), None)
    kept = lines[:start] if start is not None else lines
    if start is not None:
        kept = [ln for ln in kept if not _STATUS_LINE_RE.match(ln.strip().lstrip("-*• "))]
    return "\n".join(kept).rstrip()


def render(orders: list[Order], state: State, now: float | None = None) -> str:
    """Markdown summary for the CLI/TUI: each order with its last finding."""
    if not orders:
        return '_No standing orders yet._  `oshell orders add "keep the disk under 80%"`'
    now = now or time.time()
    glyph = {"ok": "✓", "attention": "⚠", "unknown": "?", "skipped": "·"}
    out = []
    for o in orders:
        f = state.findings.get(o.id)
        if f:
            out.append(
                f"- {glyph.get(f.status, '?')} **{o.n}.** [{o.priority}] {o.text}  "
                f"— _{f.status} {_fmt_age(f.age(now))}_" + (f": {f.note}" if f.note else "")
            )
        else:
            out.append(f"- · **{o.n}.** [{o.priority}] {o.text}  — _never checked_")
    return "\n".join(out)
