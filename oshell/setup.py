"""First-run wizard: from a bare install to a configured daily driver.

``oshell setup`` detects the machine's memory, recommends a starter set of
models sized for it (fast / deep / vision — the same slots auto-routing uses),
pulls the missing ones with live progress, persists the choices, and points at
the zsh integration. Everything is skippable; nothing is destructive.

Model picks favor the current sweet spots on ollama.com/library: gemma3 for
small+vision (tools + images in one model), qwen3 for reasoning depth.
"""

from __future__ import annotations

import platform
import subprocess

# (min unified-memory GB, slot -> model). Tiers are inclusive lower bounds,
# scanned from the top. "deep" doubles as the default model.
TIERS: list[tuple[int, dict[str, str], str]] = [
    (48, {"fast": "gemma3:4b", "deep": "qwen3:30b", "vision": "gemma3:27b"}, "48 GB+"),
    (24, {"fast": "gemma3:4b", "deep": "qwen3:14b", "vision": "gemma3:12b"}, "24–48 GB"),
    (12, {"fast": "gemma3:4b", "deep": "qwen3:8b", "vision": "gemma3:4b"}, "12–24 GB"),
    (0, {"fast": "gemma3:4b", "deep": "gemma3:4b", "vision": "gemma3:4b"}, "under 12 GB"),
]


def detect_ram_gb() -> float | None:
    """Physical memory in GB, or None when we can't tell (caller should ask)."""
    try:
        if platform.system() == "Darwin":
            out = subprocess.run(
                ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=3
            )
            return int(out.stdout.strip()) / 1024**3
        if platform.system() == "Linux":
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) / 1024**2  # kB -> GB
    except (OSError, ValueError, subprocess.TimeoutExpired):  # pragma: no cover
        pass
    return None


def _family(name: str) -> str:
    """'qwen3:8b-q4_K_M' -> 'qwen3:8b' — enough to match a rec to an install."""
    base = name.split("-")[0]
    return base


def recommend_models(ram_gb: float, installed: list[str]) -> dict:
    """The starter plan for this machine.

    Returns {"tier": label, "slots": {slot: {"model": name, "installed": bool}}}.
    A recommendation counts as installed when any installed model shares its
    family:size prefix (quant suffixes differ per pull).
    """
    slots: dict[str, str] = {}
    label = ""
    for floor, slots, label in TIERS:  # noqa: B007 - values used after the loop
        if ram_gb >= floor:
            break
    have = {_family(m) for m in installed} | set(installed)
    return {
        "tier": label,
        "slots": {
            slot: {"model": model, "installed": _family(model) in have or model in have}
            for slot, model in slots.items()
        },
    }


def run_wizard(console) -> int:
    """The interactive flow. Returns an exit code. Kept out of cli.py for size;
    imports are local so `oshell setup --help` stays instant."""
    import sys

    import typer
    from rich.panel import Panel
    from rich.table import Table

    from .cli import _pull_with_progress
    from .config import Config, update_local_config
    from .providers import get_provider

    if not sys.stdin.isatty():
        console.print("[red]oshell setup is interactive — run it in a terminal.[/red]")
        return 1

    console.print(
        Panel.fit(
            "[bold cyan]Welcome to Ollama Shell[/] — let's size it to this machine.",
            border_style="cyan",
        )
    )
    config = Config.load()
    provider = get_provider(config)
    if not provider.health():
        console.print(
            f"[red]Can't reach {config.provider.host}.[/red] Start Ollama first "
            "(https://ollama.com), then re-run [bold]oshell setup[/bold]."
        )
        return 1

    ram = detect_ram_gb()
    if ram is None:
        ram = float(typer.prompt("How much RAM does this machine have (GB)?", default=16))
    console.print(f"[dim]Detected ~{ram:.0f} GB of memory.[/dim]")

    installed = provider.list_models()
    plan = recommend_models(ram, installed)
    table = Table(title=f"Recommended for the {plan['tier']} tier")
    table.add_column("role")
    table.add_column("model")
    table.add_column("status")
    for slot, rec in plan["slots"].items():
        status = "[green]installed[/green]" if rec["installed"] else "[yellow]needs pull[/yellow]"
        table.add_row(slot, rec["model"], status)
    console.print(table)

    missing = sorted({r["model"] for r in plan["slots"].values() if not r["installed"]})
    if missing and typer.confirm(f"Pull {len(missing)} missing model(s) now?", default=True):
        for name in missing:
            try:
                _pull_with_progress(provider, name)
            except Exception as exc:
                console.print(f"[red]{exc}[/red] — skipping {name}")

    deep = plan["slots"]["deep"]["model"]
    updates: dict = {"default_model": deep}
    if typer.confirm("Enable auto model routing (fast/deep/vision per message)?", default=True):
        updates["routing"] = {
            "enabled": True,
            "fast_model": plan["slots"]["fast"]["model"],
            "deep_model": deep,
            "vision_model": plan["slots"]["vision"]["model"],
        }
    try:
        update_local_config(updates)
        console.print(f"[green]✓[/green] saved: default model {deep}"
                      + (", routing on" if "routing" in updates else ""))
    except Exception as exc:  # pragma: no cover - defensive
        console.print(f"[yellow]Could not save config: {exc}[/yellow]")

    console.print(
        Panel.fit(
            "You're set. Three things worth doing next:\n"
            '  1. add to ~/.zshrc:  [bold]eval "$(oshell init zsh)"[/bold]  (Ctrl+G superpowers)\n'
            "  2. run [bold]oshell doctor[/bold] to see the whole rig\n"
            "  3. run [bold]oshell tui[/bold] and try /daydream 💭",
            border_style="green",
            title="ready",
        )
    )
    return 0
