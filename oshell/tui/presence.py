"""In-app management of presence: standing orders, scheduled jobs, the inbox.

The rule for the whole app: nothing should require a text editor. These three
modal screens edit the same plain files the CLI does (``orders.md``, the jobs
directory, the inbox directory) with single-key actions and a hint line, in
the same keyboard-driven style as the main menu. Screens do the quick, local
edits themselves and hand anything that needs the model or a confirmation
back to the app as a small command tuple.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from .. import inbox, orders, schedule
from .menu import ConfirmScreen

_BOX_CSS = """
    #menu-box {
        width: 96; height: auto; max-height: 90%; padding: 1 2;
        border: round $accent; background: $surface;
    }
    #menu-title { padding-bottom: 1; }
    #menu-list { height: auto; max-height: 24; }
    #menu-hint { padding-top: 1; color: $text-muted; }
"""


class PromptScreen(ModalScreen[str]):
    """One line of text (add/edit an order, a job prompt, a path…)."""

    CSS = """
    PromptScreen { align: center middle; }
    #menu-box {
        width: 90; height: auto; padding: 1 2; border: round $accent; background: $surface;
    }
    #menu-title { padding-bottom: 1; }
    """
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, default: str = "", placeholder: str = "") -> None:
        super().__init__()
        self._title = title
        self._default = default
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-box"):
            yield Static(
                f"[b]{self._title}[/b]\n[dim]Enter saves · Esc cancels[/dim]", id="menu-title"
            )
            yield Input(value=self._default, placeholder=self._placeholder, id="prompt-input")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip())

    def action_cancel(self) -> None:
        self.dismiss(None)


# ── standing orders ──────────────────────────────────────────────────────────
class OrdersScreen(ModalScreen[tuple]):
    """Edit the standing orders file with single keys.

    a add · e edit · p priority · d delete · c check now · i install job · Esc.
    Returns ("check",) / ("install",) for the app to act on, or None.
    """

    CSS = "OrdersScreen { align: center middle; }" + _BOX_CSS
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("a", "add", "Add"),
        Binding("e", "edit", "Edit"),
        Binding("p", "priority", "Priority"),
        Binding("d", "delete", "Delete"),
        Binding("c", "check", "Check now"),
        Binding("i", "install", "Install job"),
    ]

    def __init__(self, orders_path: str, state_path: str, jobs_dir: str) -> None:
        super().__init__()
        self._path = orders_path
        self._state = state_path
        self._jobs = jobs_dir
        self.items: list[orders.Order] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-box"):
            yield Static("", id="menu-title")
            yield OptionList(id="menu-list")
            yield Static("", id="menu-hint")

    def on_mount(self) -> None:
        self.refresh_list()
        self.query_one(OptionList).focus()

    def refresh_list(self, highlight: int | None = None) -> None:
        self.items = orders.load_orders(self._path)
        state = orders.load_state(self._state)
        job = schedule.load_job("orders", self._jobs)
        job_line = (
            f"orders job: {job.schedule} · next {schedule.describe_when(job.next_run)} · "
            f"runs {job.runs}"
            if job
            else "no orders job yet — press [b]i[/b] to create it"
        )
        self.query_one("#menu-title", Static).update(
            f"[b]Standing orders[/b] [dim]· {escape_path(self._path)}[/dim]\n[dim]{job_line}[/dim]"
        )
        lst = self.query_one(OptionList)
        lst.clear_options()
        glyph = {"ok": "✓", "attention": "⚠", "unknown": "?", "skipped": "·"}
        color = {"high": "red", "normal": "", "low": "dim"}
        if not self.items:
            lst.add_option(Option("[dim]no orders yet — press a to add one[/dim]", disabled=True))
        for o in self.items:
            f = state.findings.get(o.id)
            row = Text()
            row.append(
                f" {glyph.get(f.status, '?') if f else '·'} ",
                style="green" if f and f.status == "ok" else ("yellow" if f else "dim"),
            )
            row.append(f"{o.n:>2}. ")
            row.append(f"[{o.priority}] ", style=color.get(o.priority, ""))
            row.append(o.text)
            if f:
                row.append(f"  — {f.status} {orders._fmt_age(f.age())}", style="dim")
                if f.note:
                    row.append(f": {f.note[:60]}", style="dim")
            lst.add_option(Option(row, id=str(o.n)))
        self.query_one("#menu-hint", Static).update(
            "[b]a[/b] add · [b]e[/b] edit · [b]p[/b] priority · [b]d[/b] delete · "
            "[b]c[/b] check now · [b]i[/b] install job · Esc close"
        )
        if self.items:
            idx = highlight if highlight is not None else 0
            lst.highlighted = max(0, min(idx, len(self.items) - 1))

    def _selected(self) -> orders.Order | None:
        idx = self.query_one(OptionList).highlighted
        if idx is None or idx >= len(self.items):
            return None
        return self.items[idx]

    def action_add(self) -> None:
        def done(text: str | None) -> None:
            if text:
                orders.add_order(text, "normal", self._path)
                self.refresh_list(highlight=len(self.items))
                self.app.notify("Order added")

        self.app.push_screen(
            PromptScreen("New standing order", placeholder="keep the disk under 80% …"), done
        )

    def action_edit(self) -> None:
        o = self._selected()
        if o is None:
            return

        def done(text: str | None) -> None:
            if text:
                orders.update_order(o.n, text=text, path=self._path)
                self.refresh_list(highlight=o.n - 1)

        self.app.push_screen(PromptScreen(f"Edit order #{o.n}", default=o.text), done)

    def action_priority(self) -> None:
        o = self._selected()
        if o is None:
            return
        new = orders.cycle_priority(o.priority)
        orders.update_order(o.n, priority=new, path=self._path)
        self.refresh_list(highlight=o.n - 1)

    def action_delete(self) -> None:
        o = self._selected()
        if o is None:
            return

        def done(yes: bool | None) -> None:
            if yes:
                orders.remove_order(o.n, self._path)
                self.refresh_list(highlight=o.n - 2)
                self.app.notify(f"Removed order #{o.n}")

        self.app.push_screen(ConfirmScreen(f"Delete order #{o.n}?\n\n[dim]{o.text}[/dim]"), done)

    def action_check(self) -> None:
        self.dismiss(("check",))

    def action_install(self) -> None:
        self.dismiss(("install",))

    def action_close(self) -> None:
        self.dismiss(None)


# ── scheduled jobs ───────────────────────────────────────────────────────────
class JobsScreen(ModalScreen[tuple]):
    """Manage jobs: n new · w watch · r run now · t pause/resume · d delete ·
    s install OS scheduler · Esc. Returns ("run", name) / ("scheduler",) or None."""

    CSS = "JobsScreen { align: center middle; }" + _BOX_CSS
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("n", "new", "New"),
        Binding("w", "watch", "Watch"),
        Binding("r", "run", "Run now"),
        Binding("t", "toggle", "Pause/resume"),
        Binding("d", "delete", "Delete"),
        Binding("s", "scheduler", "Install scheduler"),
    ]

    def __init__(self, jobs_dir: str) -> None:
        super().__init__()
        self._dir = jobs_dir
        self.items: list[schedule.Job] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-box"):
            yield Static("", id="menu-title")
            yield OptionList(id="menu-list")
            yield Static("", id="menu-hint")

    def on_mount(self) -> None:
        self.refresh_list()
        self.query_one(OptionList).focus()

    def refresh_list(self, highlight: int | None = None) -> None:
        self.items = schedule.list_jobs(self._dir)
        sched = (
            "[green]● scheduler installed[/green]"
            if schedule.installed()
            else "[yellow]○ scheduler not installed — press s[/yellow]"
        )
        self.query_one("#menu-title", Static).update(f"[b]Scheduled jobs[/b] [dim]·[/dim] {sched}")
        lst = self.query_one(OptionList)
        lst.clear_options()
        if not self.items:
            lst.add_option(
                Option(
                    "[dim]no jobs yet — n for a new one, w for a file watch[/dim]", disabled=True
                )
            )
        for j in self.items:
            row = Text()
            row.append(" ● " if j.enabled else " ○ ", style="green" if j.enabled else "dim")
            row.append(f"{j.name:<18}", style="bold" if j.enabled else "dim")
            row.append(f"{j.schedule[:34]:<35}", style="")
            row.append(
                f"next {schedule.describe_when(j.next_run) if j.enabled else '—'} · runs {j.runs}",
                style="dim",
            )
            if j.last_status:
                row.append(f" · {j.last_status}", style="green" if j.last_status == "ok" else "red")
            lst.add_option(Option(row, id=j.name))
        self.query_one("#menu-hint", Static).update(
            "[b]n[/b] new · [b]w[/b] watch a path · [b]r[/b] run now · [b]t[/b] pause/resume · "
            "[b]d[/b] delete · [b]s[/b] install scheduler · Esc"
        )
        if self.items:
            lst.highlighted = max(
                0, min(highlight if highlight is not None else 0, len(self.items) - 1)
            )

    def _selected(self) -> schedule.Job | None:
        idx = self.query_one(OptionList).highlighted
        if idx is None or idx >= len(self.items):
            return None
        return self.items[idx]

    def action_new(self) -> None:
        def got_prompt(prompt: str | None) -> None:
            if not prompt:
                return

            def got_when(when: str | None) -> None:
                if not when:
                    return
                try:
                    kw = _parse_when(when)
                    name = schedule.unique_name(prompt[:24], self._dir)
                    schedule.add_job(schedule.Job(name=name, prompt=prompt, **kw), self._dir)
                except ValueError as exc:
                    self.app.notify(str(exc), severity="error")
                    return
                self.refresh_list(highlight=len(self.items))
                self.app.notify(f"Job {name} added")

            self.app.push_screen(
                PromptScreen(
                    "When?",
                    default="every 6h",
                    placeholder="every 6h · cron 0 9 * * 1-5 · at 2026-09-05T09:00",
                ),
                got_when,
            )

        self.app.push_screen(
            PromptScreen("New job — what should it do?", placeholder="is the disk filling up?"),
            got_prompt,
        )

    def action_watch(self) -> None:
        def got_path(path: str | None) -> None:
            if not path:
                return

            def got_prompt(prompt: str | None) -> None:
                if not prompt:
                    return
                from .. import watch as watch_mod

                try:
                    spec = watch_mod.WatchSpec(path=path)
                    name = schedule.unique_name(f"watch-{schedule._slug_tail(path)}", self._dir)
                    schedule.add_job(
                        schedule.Job(name=name, prompt=prompt, kind="watch", watch=spec.to_dict()),
                        self._dir,
                    )
                    watch_mod.check(name, spec, schedule.jobs_dir(self._dir))
                except ValueError as exc:
                    self.app.notify(str(exc), severity="error")
                    return
                self.refresh_list(highlight=len(self.items))
                self.app.notify(f"Watching {path}")

            self.app.push_screen(
                PromptScreen("When it changes, do what?", placeholder="summarize the new file"),
                got_prompt,
            )

        self.app.push_screen(PromptScreen("Watch which path?", placeholder="~/Downloads"), got_path)

    def action_run(self) -> None:
        j = self._selected()
        if j is not None:
            self.dismiss(("run", j.name))

    def action_toggle(self) -> None:
        j = self._selected()
        if j is None:
            return
        j.enabled = not j.enabled
        if j.enabled:
            j.next_run = j.compute_next()
        schedule.save_job(j, self._dir)
        self.refresh_list(highlight=self.items.index(j))

    def action_delete(self) -> None:
        j = self._selected()
        if j is None:
            return
        idx = self.items.index(j)

        def done(yes: bool | None) -> None:
            if yes:
                schedule.delete_job(j.name, self._dir)
                self.refresh_list(highlight=idx - 1)
                self.app.notify(f"Deleted job {j.name}")

        self.app.push_screen(ConfirmScreen(f"Delete job [b]{j.name}[/b]?"), done)

    def action_scheduler(self) -> None:
        self.dismiss(("scheduler",))

    def action_close(self) -> None:
        self.dismiss(None)


def _parse_when(text: str) -> dict:
    """'every 6h' / 'cron 0 9 * * 1-5' / 'at 2026-09-05T09:00' / bare '6h' → Job kwargs."""
    t = text.strip()
    low = t.lower()
    if low.startswith("every "):
        return {"every": t[6:].strip()}
    if low.startswith("cron "):
        return {"cron": t[5:].strip()}
    if low.startswith("at "):
        return {"at": t[3:].strip()}
    if len(t.split()) == 5:
        return {"cron": t}
    if "T" in t or t[:4].isdigit():
        return {"at": t}
    return {"every": t}


# ── inbox ────────────────────────────────────────────────────────────────────
class InboxScreen(ModalScreen[tuple]):
    """Read notes and act on proposals: Enter show · a approve · x dismiss ·
    c clear read notes · Esc. Returns ("show", id) / ("approve", id) or None."""

    CSS = "InboxScreen { align: center middle; }" + _BOX_CSS
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("a", "approve", "Approve"),
        Binding("x", "dismiss_note", "Dismiss"),
        Binding("c", "clear", "Clear read"),
    ]

    def __init__(self, inbox_dir: str) -> None:
        super().__init__()
        self._dir = inbox_dir
        self.items: list[inbox.Note] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="menu-box"):
            yield Static("", id="menu-title")
            yield OptionList(id="menu-list")
            yield Static("", id="menu-hint")

    def on_mount(self) -> None:
        self.refresh_list()
        self.query_one(OptionList).focus()

    def refresh_list(self, highlight: int | None = None) -> None:
        notes = inbox.list_notes(directory=self._dir)
        # Actionable first, then unread, then the rest (newest first within each).
        self.items = sorted(notes, key=lambda n: (not n.pending, n.status != "unread", -n.ts))[:40]
        unread = sum(1 for n in notes if n.status == "unread")
        pend = sum(len(n.pending) for n in notes)
        self.query_one("#menu-title", Static).update(
            f"[b]Inbox[/b] [dim]· {unread} unread · {pend} action{'s' if pend != 1 else ''} "
            "to approve[/dim]"
        )
        lst = self.query_one(OptionList)
        lst.clear_options()
        if not self.items:
            lst.add_option(
                Option(
                    "[dim]inbox empty — scheduled runs leave their notes here[/dim]", disabled=True
                )
            )
        for n in self.items:
            row = Text()
            mark = "▶" if n.pending else ("●" if n.status == "unread" else "·")
            row.append(
                f" {mark} ",
                style="yellow" if n.pending else ("bold" if n.status == "unread" else "dim"),
            )
            row.append(f"{n.when}  ", style="dim")
            row.append(f"{n.job:<14}", style="cyan")
            row.append(n.title[:52], style="bold" if n.status == "unread" else "")
            if n.pending:
                row.append(f"  {len(n.pending)} to approve", style="yellow")
            elif n.error:
                row.append("  error", style="red")
            lst.add_option(Option(row, id=n.id))
        self.query_one("#menu-hint", Static).update(
            "[b]Enter[/b] read · [b]a[/b] approve actions · [b]x[/b] dismiss · "
            "[b]c[/b] clear read notes · Esc"
        )
        if self.items:
            lst.highlighted = max(
                0, min(highlight if highlight is not None else 0, len(self.items) - 1)
            )

    def _selected(self) -> inbox.Note | None:
        idx = self.query_one(OptionList).highlighted
        if idx is None or idx >= len(self.items):
            return None
        return self.items[idx]

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id:
            self.dismiss(("show", event.option.id))

    def action_approve(self) -> None:
        n = self._selected()
        if n is None:
            return
        if not n.pending:
            self.app.notify("Nothing to approve on that note")
            return
        self.dismiss(("approve", n.id))

    def action_dismiss_note(self) -> None:
        n = self._selected()
        if n is None:
            return
        for p in n.proposals:
            if p.status == "pending":
                p.status = "dismissed"
        n.status = "dismissed"
        inbox.save(n, self._dir)
        self.refresh_list(highlight=self.items.index(n))

    def action_clear(self) -> None:
        def done(yes: bool | None) -> None:
            if yes:
                k = inbox.clear(self._dir, keep_pending=True)
                self.refresh_list()
                self.app.notify(f"Deleted {k} note{'s' if k != 1 else ''}")

        self.app.push_screen(ConfirmScreen("Delete all notes without pending actions?"), done)

    def action_close(self) -> None:
        self.dismiss(None)


def escape_path(p: str) -> str:
    """Home-relative, markup-safe: ~/.oshell/orders.md."""
    full = Path(p).expanduser()
    try:
        shown = "~/" + str(full.relative_to(Path.home()))
    except ValueError:
        shown = str(full)
    return shown.replace("[", "\\[")


__all__ = ["InboxScreen", "JobsScreen", "OrdersScreen", "PromptScreen"]
_ = Callable
