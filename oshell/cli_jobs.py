"""``oshell jobs …`` and ``oshell inbox …`` — presence, from the command line.

Registered onto the main Typer app by :func:`register`.
"""

from __future__ import annotations

import time

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from . import inbox, schedule
from .config import Config


def register(app: typer.Typer, console: Console) -> None:
    jobs_app = typer.Typer(
        help="Scheduled runs: the agent wakes on a timer and reports to your inbox."
    )
    app.add_typer(jobs_app, name="jobs")

    def _dir() -> str:
        return Config.load().jobs.dir

    @jobs_app.callback(invoke_without_command=True)
    def jobs(ctx: typer.Context) -> None:
        """List scheduled jobs (or run a subcommand)."""
        if ctx.invoked_subcommand is not None:
            return
        items = schedule.list_jobs(_dir())
        if not items:
            console.print(
                "[oshell.muted]No jobs yet.[/]  "
                'oshell jobs add disk-watch --every 6h "is the disk filling up? what grew?"'
            )
            return
        table = Table(border_style="oshell.border.soft", title="jobs", title_style="oshell.title")
        table.add_column("name", style="oshell.accent")
        table.add_column("schedule")
        table.add_column("next run")
        table.add_column("runs", justify="right")
        table.add_column("last")
        table.add_column("prompt", style="oshell.muted", max_width=48)
        for j in items:
            name = j.name + ("" if j.enabled else " [oshell.muted](off)[/]")
            if j.parent:
                name += f" [oshell.muted]↳ {j.parent}[/]"
            last = {"ok": "[oshell.ok]ok[/]", "error": "[oshell.err]error[/]"}.get(
                j.last_status, "—"
            )
            table.add_row(
                name,
                j.schedule,
                schedule.describe_when(j.next_run) if j.enabled else "—",
                str(j.runs),
                last,
                escape(j.prompt[:48] + ("…" if len(j.prompt) > 48 else "")),
            )
        console.print(table)
        state = (
            "[oshell.ok]● scheduler installed[/]"
            if schedule.installed()
            else "[oshell.warn]○ scheduler not installed[/] — oshell jobs install"
        )
        console.print(f"{state}  [oshell.muted]· oshell jobs run NAME · oshell inbox[/]")

    @jobs_app.command("add")
    def jobs_add(
        name: str = typer.Argument(..., help="short name: lowercase, digits, dashes"),
        prompt: str = typer.Argument(..., help="what to do, or /command args"),
        every: str = typer.Option(None, "--every", "-e", help="interval: 30m, 6h, 1d"),
        cron: str = typer.Option(None, "--cron", "-c", help='cron line: "0 9 * * 1-5"'),
        at: str = typer.Option(None, "--at", help="one-shot ISO datetime"),
        role: str = typer.Option(None, "--role", help="a role for the run (oshell roles)"),
        model: str = typer.Option(None, "--model", "-m"),
        approvals: str = typer.Option("ask", "--approvals", help="ask | read-only | auto"),
        max_iterations: int = typer.Option(6, "--rounds", help="tool-round budget"),
        timeout: int = typer.Option(300, "--timeout", help="wall-clock budget (seconds)"),
        no_notify: bool = typer.Option(False, "--no-notify", help="no desktop notification"),
        replace: bool = typer.Option(False, "--replace", help="overwrite an existing job"),
    ) -> None:
        """Add a job. Sensitive actions queue in the inbox unless --approvals auto."""
        try:
            job = schedule.Job(
                name=name,
                prompt=prompt,
                every=every,
                cron=cron,
                at=at,
                role=role,
                model=model,
                approvals=approvals,
                max_iterations=max_iterations,
                timeout=timeout,
                notify=not no_notify,
            )
            schedule.add_job(job, _dir(), replace=replace)
        except (ValueError, FileExistsError) as exc:
            console.print(f"[oshell.err]{exc}[/]")
            raise typer.Exit(code=1) from None
        console.print(
            f"[oshell.ok]✓[/] {job.name} · {job.schedule} · next "
            f"{schedule.describe_when(job.next_run)}"
        )
        if approvals == "auto":
            console.print(
                "[oshell.warn]⚠ approvals=auto: this job may run sensitive commands unattended.[/]"
            )
        if not schedule.installed():
            console.print(
                "[oshell.muted]The OS scheduler isn't installed yet — nothing runs until: "
                "oshell jobs install[/]"
            )

    @jobs_app.command("watch")
    def jobs_watch(
        name: str = typer.Argument(..., help="short name"),
        path: str = typer.Argument(..., help="file or directory to watch"),
        prompt: str = typer.Argument(..., help="what to do when it changes"),
        pattern: str = typer.Option("*", "--pattern", help="glob filter, e.g. '*.log'"),
        on: str = typer.Option("any", "--on", help="any | created | modified | deleted"),
        settle: int = typer.Option(10, "--settle", help="seconds unchanged before it counts"),
        recursive: bool = typer.Option(False, "--recursive", "-r", help="walk subdirectories"),
        every: str = typer.Option("1m", "--every", help="rescan interval"),
        role: str = typer.Option(None, "--role"),
        approvals: str = typer.Option("ask", "--approvals", help="ask | read-only | auto"),
        replace: bool = typer.Option(False, "--replace"),
    ) -> None:
        """Run PROMPT when files under PATH change (created/modified/deleted, settled).

        Nothing runs until something changes: the minute-tick only rescans the path.
        """
        from . import watch as watch_mod

        try:
            spec = watch_mod.WatchSpec(
                path=path, pattern=pattern, event=on, settle=settle, recursive=recursive
            )
            job = schedule.Job(
                name=name,
                prompt=prompt,
                kind="watch",
                watch=spec.to_dict(),
                every=every,
                role=role,
                approvals=approvals,
            )
            schedule.add_job(job, _dir(), replace=replace)
            # Baseline now: report only what happens from here on.
            watch_mod.check(job.name, spec, schedule.jobs_dir(_dir()))
        except (ValueError, FileExistsError) as exc:
            console.print(f"[oshell.err]{exc}[/]")
            raise typer.Exit(code=1) from None
        console.print(f"[oshell.ok]✓[/] {job.name} · {job.schedule} · rescans {every}")
        if not schedule.installed():
            console.print("[oshell.muted]Scheduler not installed yet — oshell jobs install[/]")

    @jobs_app.command("rm")
    def jobs_rm(name: str) -> None:
        """Delete a job."""
        try:
            schedule.delete_job(name, _dir())
        except FileNotFoundError as exc:
            console.print(f"[oshell.err]{exc}[/]")
            raise typer.Exit(code=1) from None
        console.print(f"[oshell.ok]✓[/] removed {name}")

    @jobs_app.command("show")
    def jobs_show(name: str) -> None:
        """Print a job's definition and its last note."""
        job = schedule.load_job(name, _dir())
        if job is None:
            console.print(f"[oshell.err]no job named {name}[/]")
            raise typer.Exit(code=1)
        import json
        from dataclasses import asdict

        console.print_json(data=asdict(job))
        cfg = Config.load()
        last = inbox.latest_for_job(name, cfg.jobs.inbox_dir)
        if last:
            console.print(
                Panel(Markdown(inbox.render_markdown(last)), border_style="oshell.border.soft")
            )
        _ = json

    @jobs_app.command("enable")
    def jobs_enable(
        name: str, off: bool = typer.Option(False, "--off", help="disable instead")
    ) -> None:
        """Enable (or --off: disable) a job without deleting it."""
        job = schedule.load_job(name, _dir())
        if job is None:
            console.print(f"[oshell.err]no job named {name}[/]")
            raise typer.Exit(code=1)
        job.enabled = not off
        if job.enabled:
            job.next_run = job.compute_next()
        schedule.save_job(job, _dir())
        console.print(f"[oshell.ok]✓[/] {name} {'enabled' if job.enabled else 'disabled'}")

    @jobs_app.command("run")
    def jobs_run(
        name: str,
        quiet: bool = typer.Option(False, "--quiet", "-q", help="don't stream the run"),
    ) -> None:
        """Run a job right now, in the foreground, and file its note."""
        from .agent import TextDelta, ToolFinished, ToolStarted

        cfg = Config.load()
        job = schedule.load_job(name, cfg.jobs.dir)
        if job is None:
            console.print(f"[oshell.err]no job named {name}[/]")
            raise typer.Exit(code=1)

        streaming = [False]

        def show(event) -> None:
            if quiet:
                return
            if isinstance(event, TextDelta):
                console.print(event.text, end="")
                streaming[0] = True
            elif isinstance(event, ToolStarted):
                if streaming[0]:
                    console.print()
                    streaming[0] = False
                console.print(
                    f"[oshell.muted]⚙ {escape(event.name)}({escape(str(event.arguments)[:100])})[/]"
                )
            elif isinstance(event, ToolFinished):
                console.print(
                    f"[oshell.muted]  ↳ {escape(event.result.replace(chr(10), ' ')[:120])}[/]"
                )

        console.print(
            f"[oshell.muted]running {job.name} ({job.schedule}) · {job.max_iterations} rounds…[/]"
        )
        result = schedule.run_job(
            job, cfg, directory=cfg.jobs.dir, inbox_dir=cfg.jobs.inbox_dir, on_event=show
        )
        console.print()
        if result.note:
            console.print(
                Panel(
                    Markdown(inbox.render_markdown(result.note)),
                    title=f"[oshell.accent]inbox · {result.note.id}[/]",
                    border_style="oshell.border" if result.status == "ok" else "oshell.err",
                )
            )
        if result.status != "ok":
            raise typer.Exit(code=1)

    @jobs_app.command("tick")
    def jobs_tick() -> None:
        """Run whatever is due (what the OS scheduler calls every minute)."""
        cfg = Config.load()
        due = schedule.due_jobs(directory=cfg.jobs.dir)
        if not due:
            return  # the common case: nothing to do, exit in milliseconds
        for job in due:
            r = schedule.run_job(job, cfg, directory=cfg.jobs.dir, inbox_dir=cfg.jobs.inbox_dir)
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            title = r.note.title if r.note else r.status
            print(f"{stamp} {job.name}: {r.status} — {title}")

    @jobs_app.command("install")
    def jobs_install(
        interval: int = typer.Option(60, "--interval", help="seconds between ticks"),
        dry_run: bool = typer.Option(False, "--dry-run", help="show what would be installed"),
    ) -> None:
        """Register `oshell jobs tick` with launchd / systemd --user / Task Scheduler."""
        desc, cmds, files = schedule.install_plan(interval)
        if dry_run:
            console.print(f"[oshell.accent]{desc}[/]")
            for path, text in files.items():
                console.print(
                    Panel(escape(text), title=str(path), border_style="oshell.border.soft")
                )
            for c in cmds:
                console.print(f"[oshell.muted]$ {' '.join(c)}[/]")
            return
        try:
            schedule.install(interval)
        except RuntimeError as exc:
            console.print(f"[oshell.err]{exc}[/]")
            raise typer.Exit(code=1) from None
        console.print(f"[oshell.ok]✓[/] {desc}  [oshell.muted]log: ~/.oshell/jobs.log[/]")

    @jobs_app.command("uninstall")
    def jobs_uninstall() -> None:
        """Remove the OS scheduler entry (jobs stay on disk)."""
        console.print(f"[oshell.ok]✓[/] {schedule.uninstall()}")

    # ── standing orders ──────────────────────────────────────────────────────
    orders_app = typer.Typer(help="Standing orders: outcomes to keep true (~/.oshell/orders.md).")
    app.add_typer(orders_app, name="orders")

    def _ocfg():
        return Config.load().jobs

    @orders_app.callback(invoke_without_command=True)
    def orders(ctx: typer.Context) -> None:
        """Show the standing orders and what was last found for each."""
        if ctx.invoked_subcommand is not None:
            return
        from . import orders as orders_mod

        jc = _ocfg()
        items = orders_mod.load_orders(jc.orders_path)
        state = orders_mod.load_state(jc.orders_state)
        console.print(
            Panel(
                Markdown(orders_mod.render(items, state)),
                title="[oshell.accent]standing orders[/]",
                border_style="oshell.border.soft",
            )
        )
        job = schedule.load_job("orders", jc.dir)
        if job is None:
            console.print(
                "[oshell.muted]No orders job yet — nothing checks these until:  "
                "oshell orders install[/]"
            )
        else:
            console.print(
                f"[oshell.muted]orders job: {job.schedule} · next "
                f"{schedule.describe_when(job.next_run)} · runs {job.runs}"
                + (
                    ""
                    if schedule.installed()
                    else " · scheduler not installed (oshell jobs install)"
                )
                + "[/]"
            )
        console.print(
            f"[oshell.muted]edit: {orders_mod.orders_path(jc.orders_path)}  · "
            'oshell orders add "…" [--priority high] · rm N · check[/]'
        )

    @orders_app.command("add")
    def orders_add(
        text: str = typer.Argument(..., help="the order, in plain language"),
        priority: str = typer.Option("normal", "--priority", "-p", help="high | normal | low"),
    ) -> None:
        """Append an order to ~/.oshell/orders.md."""
        from . import orders as orders_mod

        try:
            o = orders_mod.add_order(text, priority, _ocfg().orders_path)
        except ValueError as exc:
            console.print(f"[oshell.err]{exc}[/]")
            raise typer.Exit(code=1) from None
        console.print(f"[oshell.ok]✓[/] #{o.n} [{o.priority}] {escape(o.text)}")

    @orders_app.command("rm")
    def orders_rm(n: int = typer.Argument(..., help="order number (oshell orders)")) -> None:
        """Remove order #N."""
        from . import orders as orders_mod

        try:
            o = orders_mod.remove_order(n, _ocfg().orders_path)
        except (IndexError, OSError) as exc:
            console.print(f"[oshell.err]{exc}[/]")
            raise typer.Exit(code=1) from None
        console.print(f"[oshell.ok]✓[/] removed #{n}: {escape(o.text)}")

    @orders_app.command("edit")
    def orders_edit() -> None:
        """Open orders.md in $EDITOR."""
        import os
        import subprocess

        from . import orders as orders_mod

        path = orders_mod.ensure_file(_ocfg().orders_path)
        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "nano"
        subprocess.run([editor, str(path)])

    @orders_app.command("install")
    def orders_install(
        every: str = typer.Option(None, "--every", help="how often to wake (default 1h)"),
        role: str = typer.Option("sysadmin", "--role"),
        replace: bool = typer.Option(False, "--replace"),
    ) -> None:
        """Create the `orders` job (and the orders file if missing)."""
        from . import orders as orders_mod

        jc = _ocfg()
        orders_mod.ensure_file(jc.orders_path)
        try:
            job = schedule.Job(
                name="orders",
                prompt="Check the standing orders.",
                kind="orders",
                every=every or jc.orders_every,
                role=role,
                max_iterations=10,
            )
            schedule.add_job(job, jc.dir, replace=replace)
        except FileExistsError:
            console.print("[oshell.muted]orders job already exists (use --replace)[/]")
            return
        except ValueError as exc:
            console.print(f"[oshell.err]{exc}[/]")
            raise typer.Exit(code=1) from None
        console.print(
            f"[oshell.ok]✓[/] orders job · {job.schedule} · file: "
            f"{orders_mod.orders_path(jc.orders_path)}"
        )
        if not schedule.installed():
            console.print("[oshell.muted]Scheduler not installed yet — oshell jobs install[/]")

    @orders_app.command("check")
    def orders_check() -> None:
        """Check the standing orders right now (runs the orders job in the foreground)."""
        cfg = Config.load()
        job = schedule.load_job("orders", cfg.jobs.dir)
        if job is None:
            from . import orders as orders_mod

            orders_mod.ensure_file(cfg.jobs.orders_path)
            job = schedule.Job(
                name="orders",
                prompt="Check the standing orders.",
                kind="orders",
                every=cfg.jobs.orders_every,
                role="sysadmin",
                max_iterations=10,
            )
            schedule.add_job(job, cfg.jobs.dir)
        jobs_run(name="orders", quiet=False)

    # ── inbox ────────────────────────────────────────────────────────────────
    inbox_app = typer.Typer(help="Notes and proposed actions from scheduled runs.")
    app.add_typer(inbox_app, name="inbox")

    def _idir() -> str:
        return Config.load().jobs.inbox_dir

    @inbox_app.callback(invoke_without_command=True)
    def inbox_list(
        ctx: typer.Context,
        all_: bool = typer.Option(False, "--all", "-a", help="include read/dismissed notes"),
    ) -> None:
        """List notes (unread and pending first)."""
        if ctx.invoked_subcommand is not None:
            return
        notes = inbox.list_notes(directory=_idir())
        if not all_:
            notes = [n for n in notes if n.status == "unread" or n.pending]
        if not notes:
            console.print(
                "[oshell.muted]Inbox empty.[/]" + ("" if all_ else "  (--all for history)")
            )
            return
        table = Table(border_style="oshell.border.soft", title="inbox", title_style="oshell.title")
        table.add_column("id", style="oshell.accent")
        table.add_column("when", style="oshell.muted")
        table.add_column("job")
        table.add_column("title")
        table.add_column("actions")
        for n in notes:
            pend = len(n.pending)
            acts = (
                f"[oshell.warn]{pend} to approve[/]"
                if pend
                else ("[oshell.err]error[/]" if n.error else "")
            )
            title = escape(n.title[:60])
            if n.status == "unread":
                title = f"[bold]{title}[/]"
            table.add_row(n.id, n.when, n.job, title, acts)
        console.print(table)
        console.print("[oshell.muted]oshell inbox show ID · approve ID · dismiss ID · clear[/]")

    @inbox_app.command("show")
    def inbox_show(note_id: str) -> None:
        """Print a note (marks it read)."""
        note = inbox.get(note_id, _idir())
        if note is None:
            console.print(f"[oshell.err]no note {note_id}[/]")
            raise typer.Exit(code=1)
        console.print(
            Panel(Markdown(inbox.render_markdown(note)), border_style="oshell.border.soft")
        )
        if note.status == "unread":
            inbox.mark(note.id, "read", _idir())

    @inbox_app.command("approve")
    def inbox_approve(
        note_id: str,
        index: int = typer.Option(None, "--index", "-i", help="only this proposal (1-based)"),
        yes: bool = typer.Option(False, "--yes", "-y", help="don't confirm each one"),
    ) -> None:
        """Run a note's proposed actions — each shown and confirmed first."""
        cfg = Config.load()
        note = inbox.get(note_id, _idir())
        if note is None:
            console.print(f"[oshell.err]no note {note_id}[/]")
            raise typer.Exit(code=1)
        pending = [(i, p) for i, p in enumerate(note.proposals, 1) if p.status == "pending"]
        if index is not None:
            pending = [(i, p) for i, p in pending if i == index]
        if not pending:
            console.print("[oshell.muted]nothing pending on that note[/]")
            return
        from .memory import MemoryStore
        from .providers import get_provider
        from .providers.base import ToolCall
        from .tools import default_registry

        run_cfg = cfg.model_copy(deep=True)
        run_cfg.approvals = "auto"  # the human is the approval
        registry = default_registry(
            get_provider(run_cfg), run_cfg, memory=MemoryStore(run_cfg.memory.path)
        )
        for i, p in pending:
            console.print(
                Panel(
                    escape(p.summary),
                    title=f"[oshell.accent]proposal {i}[/]",
                    border_style="oshell.border",
                    expand=False,
                )
            )
            if not yes and not typer.confirm("Run it?", default=False):
                p.status = "dismissed"
                continue
            try:
                out = registry.dispatch(ToolCall(name=p.tool, arguments=p.arguments))
                p.status, p.result = "approved", out
                console.print(f"[oshell.ok]✓[/] {escape(out[:400])}")
            except Exception as exc:
                p.status, p.result = "failed", str(exc)
                console.print(f"[oshell.err]{exc}[/]")
        note.status = "approved" if any(p.status == "approved" for p in note.proposals) else "read"
        inbox.save(note, _idir())

    @inbox_app.command("dismiss")
    def inbox_dismiss(note_id: str) -> None:
        """Mark a note dismissed (its proposals will never run)."""
        note = inbox.get(note_id, _idir())
        if note is None:
            console.print(f"[oshell.err]no note {note_id}[/]")
            raise typer.Exit(code=1)
        for p in note.proposals:
            if p.status == "pending":
                p.status = "dismissed"
        note.status = "dismissed"
        inbox.save(note, _idir())
        console.print(f"[oshell.ok]✓[/] dismissed {note.id}")

    @inbox_app.command("clear")
    def inbox_clear(
        everything: bool = typer.Option(
            False, "--all", help="also delete notes with pending actions"
        ),
    ) -> None:
        """Delete notes (keeps ones with pending actions unless --all)."""
        n = inbox.clear(_idir(), keep_pending=not everything)
        console.print(f"[oshell.ok]✓[/] deleted {n} note{'s' if n != 1 else ''}")
