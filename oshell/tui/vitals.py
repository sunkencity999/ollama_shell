"""The vitals tile — a small btop for the workspace.

A riced desktop always has a monitor open somewhere: CPU and memory
sparklines, what's on the GPU, load. Ours is one tile: CPU and RAM history,
what Ollama has loaded (and how much of it sits on the GPU), the last turns'
tokens/second, context fill, uptime — sampled every couple of seconds in a
worker thread, drawn from a pure ``render_vitals`` so it's testable.

Sampling is stdlib-first (``/proc`` on Linux, ``vm_stat``/``ps`` on macOS,
``psutil`` if it happens to be installed) and never raises: a failed probe
shows as ``—``, not a traceback.
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
import time
from collections import deque
from dataclasses import dataclass, field

from rich.text import Text
from textual.widgets import Static

SPARK = "▁▂▃▄▅▆▇█"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")


@dataclass
class VitalsSample:
    cpu_pct: float | None = None
    mem_used_gb: float | None = None
    mem_total_gb: float | None = None
    load1: float | None = None
    loaded: list[dict] = field(default_factory=list)  # provider.loaded_models()
    tok_s: float | None = None
    ctx_fill: float = 0.0
    uptime: str = ""
    n_tools: int = 0
    n_net: int = 0

    @property
    def mem_pct(self) -> float | None:
        if self.mem_used_gb is None or not self.mem_total_gb:
            return None
        return max(0.0, min(100.0, 100.0 * self.mem_used_gb / self.mem_total_gb))


def sparkline(values: list[float], width: int, lo: float = 0.0, hi: float = 100.0) -> str:
    """Right-aligned sparkline of the last ``width`` values in [lo, hi]."""
    vals = list(values)[-width:]
    out = []
    span = max(hi - lo, 1e-9)
    for v in vals:
        idx = int(round((max(lo, min(hi, v)) - lo) / span * (len(SPARK) - 1)))
        out.append(SPARK[idx])
    return "".join(out).rjust(width, " ")


def bar(pct: float | None, cells: int = 10) -> str:
    if pct is None:
        return "▱" * cells
    on = int(round(max(0.0, min(100.0, pct)) / 100 * cells))
    return "▰" * on + "▱" * (cells - on)


# ── probes ───────────────────────────────────────────────────────────────────
_prev_cpu: tuple[float, float] | None = None  # (busy, total) jiffies for /proc/stat


def cpu_percent() -> float | None:
    """Whole-machine CPU %, best effort (psutil when installed — the [tui] extra
    pulls it in — else /proc on Linux, ``ps`` on macOS, load average elsewhere)."""
    global _prev_cpu
    try:
        import psutil  # optional

        return float(psutil.cpu_percent(interval=None))
    except ImportError:
        pass
    try:
        if platform.system() == "Linux":
            with open("/proc/stat", encoding="utf-8") as f:
                parts = f.readline().split()[1:]
            nums = [float(x) for x in parts]
            idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
            total = sum(nums)
            if _prev_cpu is not None:
                d_total = total - _prev_cpu[1]
                d_idle = idle - _prev_cpu[0]
                _prev_cpu = (idle, total)
                if d_total > 0:
                    return max(0.0, min(100.0, 100.0 * (1 - d_idle / d_total)))
            _prev_cpu = (idle, total)
        if platform.system() == "Darwin":
            out = subprocess.run(
                ["ps", "-A", "-o", "%cpu="], capture_output=True, text=True, timeout=2
            ).stdout
            total = sum(float(x) for x in out.split() if x.replace(".", "", 1).isdigit())
            return max(0.0, min(100.0, total / max(os.cpu_count() or 1, 1)))
    except Exception:
        pass
    try:  # last resort: load average as a share of the cores
        return max(0.0, min(100.0, 100.0 * os.getloadavg()[0] / max(os.cpu_count() or 1, 1)))
    except (AttributeError, OSError):
        return None


def memory_gb() -> tuple[float | None, float | None]:
    """(used, total) in GB, best effort."""
    try:
        import psutil  # optional

        vm = psutil.virtual_memory()
        return round((vm.total - vm.available) / 1e9, 1), round(vm.total / 1e9, 1)
    except ImportError:
        pass
    from ..tools.system import _total_ram_gb

    total = _total_ram_gb()
    try:
        if platform.system() == "Windows":
            import ctypes

            class _MemStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = _MemStatus()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
            used = (stat.ullTotalPhys - stat.ullAvailPhys) / 1e9
            return round(used, 1), round(stat.ullTotalPhys / 1e9, 1)
        if platform.system() == "Linux":
            info: dict[str, float] = {}
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    k, _, v = line.partition(":")
                    info[k] = float(v.split()[0]) * 1024
            used = info["MemTotal"] - info.get("MemAvailable", info.get("MemFree", 0))
            return round(used / 1e9, 1), round(info["MemTotal"] / 1e9, 1)
        if platform.system() == "Darwin":
            out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=2).stdout
            page = 4096
            m = re.search(r"page size of (\d+) bytes", out)
            if m:
                page = int(m.group(1))
            pages: dict[str, int] = {}
            for line in out.splitlines()[1:]:
                k, _, v = line.partition(":")
                v = v.strip().rstrip(".")
                if v.isdigit():
                    pages[k.strip()] = int(v)
            used_pages = (
                pages.get("Pages active", 0)
                + pages.get("Pages wired down", 0)
                + pages.get("Pages occupied by compressor", 0)
            )
            return round(used_pages * page / 1e9, 1), total
    except Exception:
        pass
    return None, total


def load1() -> float | None:
    try:
        return round(os.getloadavg()[0], 1)
    except (AttributeError, OSError):
        return None


def uptime_str() -> str:
    from ..fetch import _uptime

    return _uptime()


# ── rendering ────────────────────────────────────────────────────────────────
def render_vitals(
    s: VitalsSample,
    cpu_hist: list[float],
    mem_hist: list[float],
    tps_hist: list[float],
    width: int,
    colors: dict[str, str],
) -> Text:
    """The tile body for ``width`` columns."""
    fg = colors.get("foreground", "#c0caf5")
    accent = colors.get("primary", "#7aa2f7")
    muted = colors.get("text-muted", "#565f89")
    ok = colors.get("success", "#9ece6a")
    warn = colors.get("warning", "#e0af68")
    err = colors.get("error", "#f7768e")
    sec = colors.get("secondary", "#bb9af7")

    def heat(pct: float | None) -> str:
        if pct is None:
            return muted
        return err if pct > 85 else (warn if pct > 60 else ok)

    # Room for "cpu " + spark + " 100%  load 12.3" without wrapping.
    spark_w = max(6, min(24, width - 26))
    t = Text(no_wrap=True, overflow="ellipsis")

    cpu = s.cpu_pct
    t.append("cpu ", style=f"bold {accent}")
    t.append(sparkline(cpu_hist, spark_w), style=heat(cpu))
    t.append(f" {cpu:3.0f}%" if cpu is not None else "   —", style=fg)
    if s.load1 is not None:
        t.append(f"  load {s.load1}", style=muted)
    t.append("\n")

    mem = s.mem_pct
    t.append("mem ", style=f"bold {accent}")
    t.append(sparkline(mem_hist, spark_w), style=heat(mem))
    t.append(f" {mem:3.0f}%" if mem is not None else "   —", style=fg)
    if s.mem_used_gb is not None and s.mem_total_gb:
        t.append(f"  {s.mem_used_gb:.0f}/{s.mem_total_gb:.0f} GB", style=muted)
    t.append("\n")

    t.append("gpu ", style=f"bold {accent}")
    if s.loaded:
        for i, m in enumerate(s.loaded[:2]):
            if i:
                t.append("\n    ")
            name = str(m.get("name", "?"))
            size = m.get("size") or 0
            vram = m.get("size_vram") or 0
            share = (100.0 * vram / size) if size else None
            t.append(name, style=f"bold {fg}")
            if size:
                t.append(f"  {size / 1e9:.0f} GB", style=muted)
            if share is not None:
                t.append(f"  {share:.0f}% GPU", style=ok if share >= 99 else warn)
    else:
        t.append("nothing loaded", style=muted)
    t.append("\n")

    t.append("tps ", style=f"bold {accent}")
    hi = max(tps_hist) if tps_hist else 1.0
    t.append(sparkline(tps_hist, spark_w, 0.0, max(hi, 1.0)), style=sec)
    t.append(f" {s.tok_s:3.0f}" if s.tok_s else "   —", style=fg)
    t.append(" tok/s", style=muted)
    t.append("\n")

    t.append("ctx ", style=f"bold {accent}")
    t.append(bar(100 * s.ctx_fill), style=heat(100 * s.ctx_fill))
    t.append(f" {s.ctx_fill:.0%}", style=fg)
    t.append("\n    ")
    tail = f"{s.n_tools} tools · " + (f"{s.n_net} net" if s.n_net else "fully local")
    t.append(tail, style=warn if s.n_net else ok)
    if s.uptime:
        t.append(f" · up {s.uptime}", style=muted)
    return t


class VitalsPanel(Static):
    """The tile widget; ``show`` takes a sample and repaints."""

    DEFAULT_CSS = """
    VitalsPanel { height: auto; padding: 0 1; }
    """

    HISTORY = 40

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self.cpu_hist: deque[float] = deque(maxlen=self.HISTORY)
        self.mem_hist: deque[float] = deque(maxlen=self.HISTORY)
        self.tps_hist: deque[float] = deque(maxlen=self.HISTORY)
        self.sample = VitalsSample()
        self.text = ""

    def show(self, s: VitalsSample) -> None:
        self.sample = s
        if s.cpu_pct is not None:
            self.cpu_hist.append(s.cpu_pct)
        if s.mem_pct is not None:
            self.mem_hist.append(s.mem_pct)
        if s.tok_s:
            if not self.tps_hist or self.tps_hist[-1] != s.tok_s:
                self.tps_hist.append(s.tok_s)
        self.repaint()

    def repaint(self) -> None:
        try:
            colors = {
                k: v[:7]
                for k, v in self.app.theme_variables.items()
                if isinstance(v, str) and _HEX.match(v)
            }
        except Exception:  # pragma: no cover - before the app is ready
            colors = {}
        width = (self.size.width or 44) - 4  # border + padding
        body = render_vitals(
            self.sample,
            list(self.cpu_hist),
            list(self.mem_hist),
            list(self.tps_hist),
            width,
            colors,
        )
        self.text = body.plain
        self.update(body)


def take_sample(
    provider, tok_s: float | None, ctx_fill: float, n_tools: int, n_net: int
) -> VitalsSample:
    """Everything the tile shows, gathered in one go (call from a worker thread)."""
    used, total = memory_gb()
    loaded: list[dict] = []
    try:
        loaded = list(provider.loaded_models())
    except Exception:
        loaded = []
    return VitalsSample(
        cpu_pct=cpu_percent(),
        mem_used_gb=used,
        mem_total_gb=total,
        load1=load1(),
        loaded=loaded,
        tok_s=tok_s,
        ctx_fill=ctx_fill,
        uptime=uptime_str(),
        n_tools=n_tools,
        n_net=n_net,
    )


_ = time  # kept for callers that time their sampling loops
