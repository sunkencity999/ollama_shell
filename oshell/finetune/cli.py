"""`oshell finetune` subcommands: detect / create / start / status / list."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from ..config import Config
from .datasets import DatasetError
from .hardware import detect_hardware
from .manager import FineTuneError, FineTuneManager

finetune_app = typer.Typer(help="Local LoRA fine-tuning (MLX on Apple Silicon).")
console = Console()


def _manager() -> FineTuneManager:
    return FineTuneManager(Config.load())


@finetune_app.command("detect")
def detect() -> None:
    """Show the detected training backend for this machine."""
    hw = detect_hardware()
    color = "green" if hw.can_train else "yellow"
    console.print(f"platform: [bold]{hw.platform}[/]   framework: [{color}]{hw.framework}[/]")
    if not hw.can_train:
        console.print("[yellow]No supported training accelerator detected.[/yellow]")


@finetune_app.command("create")
def create(
    name: str = typer.Argument(..., help="A label for the job"),
    model: str = typer.Option(..., "--model", "-m", help="Base HF model id"),
    dataset: str = typer.Option(..., "--dataset", "-d", help="Path to jsonl/json/csv/txt"),
) -> None:
    """Prepare a dataset and register a job (does not start training)."""
    try:
        job = _manager().create_job(name, model, dataset)
    except (DatasetError, FineTuneError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from None
    console.print(f"[green]created[/green] job [bold]{job.id}[/] (status: {job.status})")
    console.print(f"  data: {job.dataset_dir}")


@finetune_app.command("start")
def start(job_id: str = typer.Argument(..., help="Job id from `create`")) -> None:
    """Launch MLX training for a prepared job."""
    mgr = _manager()
    try:
        job = mgr.start_job(mgr.get_job(job_id))
    except FineTuneError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from None
    console.print(f"[green]started[/green] {job.id} (pid {job.pid}); log: {job.log_file}")


@finetune_app.command("status")
def status(job_id: str = typer.Argument(..., help="Job id")) -> None:
    """Show one job's current status (refreshes running jobs)."""
    mgr = _manager()
    try:
        job = mgr.refresh_status(mgr.get_job(job_id))
    except FineTuneError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from None
    console.print(f"[bold]{job.id}[/]  status: {job.status}  model: {job.base_model}")
    console.print(f"  adapters: {job.adapter_dir}")


@finetune_app.command("list")
def list_jobs() -> None:
    """List all known fine-tuning jobs."""
    mgr = _manager()
    table = Table(title="Fine-tuning jobs")
    for col in ("id", "name", "status", "base model", "created"):
        table.add_column(col)
    for job in mgr.list_jobs():
        mgr.refresh_status(job)
        table.add_row(job.id, job.name, job.status, job.base_model, job.created_at)
    console.print(table)
