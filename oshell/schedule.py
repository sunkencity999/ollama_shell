"""Scheduled runs — the agent wakes up on a timer, with context, and reports.

A **job** is a prompt (or a ``/command``) plus a schedule: an interval
(``every: 6h``), a cron line (``cron: 0 9 * * 1-5``), or a one-shot (``at``).
Jobs are JSON files in ``~/.oshell/jobs/``; the OS scheduler (launchd,
systemd user timers, Task Scheduler) runs ``oshell jobs tick`` once a minute,
which runs whatever is due and otherwise exits in milliseconds — no daemon,
no model warmed for nothing.

Each run is a fresh, non-interactive agent with the job's budget (tool
rounds, wall clock) and its **previous note** in context, so a watch has
continuity. Sensitive tools never run unattended: the approver queues them as
proposals in the inbox and tells the model so. The model may schedule its own
follow-ups with the ``schedule_followup`` tool (a one-shot child job) — the
user asked for that latitude; destructive actions stay gated regardless.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import inbox
from . import orders as orders_mod
from . import watch as watch_mod
from .config import Config

DEFAULT_DIR = "~/.oshell/jobs"
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_INTERVAL_RE = re.compile(r"^\s*(\d+)\s*([smhd])\s*$", re.I)
_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

# The job currently running (set by run_job) — the follow-up tool reads it to
# record parentage. Module-level on purpose: tools are constructed once.
CURRENT_JOB: str | None = None

SCHEDULED_RUN_PROMPT = """\
## Scheduled run
You are running **unattended** as the scheduled job `{name}` ({schedule}); nobody is \
at the keyboard. Do the task, then write a short report in markdown: what you checked, \
what you found, what (if anything) needs the user. Lead with the conclusion. If nothing \
changed, say so in one line — brevity is respect for the reader's morning.
Read-only shell commands (df, du, ls, ps, git status, docker ps, …) run normally. Commands \
that would change the machine, and GUI control, do not run in this mode: they are queued in \
the user's inbox for approval. If a tool result says "[queued]", note in your report what you \
queued and why, then continue with read-only work.
To check on something again later, call `schedule_followup` (e.g. delay "30m"). \
Don't schedule more than one follow-up per run.
{previous}"""


# ── schedule parsing ─────────────────────────────────────────────────────────
def parse_interval(text: str) -> int:
    """'15m' → 900 seconds. Units: s m h d."""
    m = _INTERVAL_RE.match(text or "")
    if not m:
        raise ValueError(f"bad interval {text!r} (use e.g. 30s, 15m, 6h, 1d)")
    n, unit = int(m.group(1)), m.group(2).lower()
    if n <= 0:
        raise ValueError("interval must be positive")
    return n * _UNITS[unit]


def _cron_field(spec: str, lo: int, hi: int) -> set[int]:
    """Expand one cron field ('*', '*/15', '1-5', '1,3,5', '0-30/10') to a set."""
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        step = 1
        if "/" in part:
            part, step_s = part.split("/", 1)
            step = int(step_s)
            if step <= 0:
                raise ValueError("cron step must be positive")
        if part in ("*", ""):
            rng = range(lo, hi + 1)
        elif "-" in part:
            a, b = part.split("-", 1)
            rng = range(int(a), int(b) + 1)
        else:
            v = int(part)
            rng = range(v, v + 1)
        for v in rng:
            if v < lo or v > hi:
                raise ValueError(f"cron value {v} out of range {lo}-{hi}")
            if (v - rng.start) % step == 0:
                out.add(v)
    return out


@dataclass(frozen=True)
class Cron:
    minutes: frozenset[int]
    hours: frozenset[int]
    days: frozenset[int]
    months: frozenset[int]
    weekdays: frozenset[int]  # 0 = Sunday … 6 = Saturday (7 → 0)
    day_star: bool
    dow_star: bool

    @classmethod
    def parse(cls, expr: str) -> Cron:
        fields = (expr or "").split()
        if len(fields) != 5:
            raise ValueError("cron needs 5 fields: minute hour day month weekday")
        mi, ho, da, mo, dw = fields
        dw_norm = dw.replace("7", "0") if dw.strip() != "*" else dw
        return cls(
            minutes=frozenset(_cron_field(mi, 0, 59)),
            hours=frozenset(_cron_field(ho, 0, 23)),
            days=frozenset(_cron_field(da, 1, 31)),
            months=frozenset(_cron_field(mo, 1, 12)),
            weekdays=frozenset(_cron_field(dw_norm, 0, 6)),
            day_star=da.strip() == "*",
            dow_star=dw.strip() == "*",
        )

    def _day_ok(self, t: dt.datetime) -> bool:
        dom = t.day in self.days
        dow = ((t.weekday() + 1) % 7) in self.weekdays  # python: Mon=0 → cron Sun=0
        if self.day_star and self.dow_star:
            return True
        if self.day_star:
            return dow
        if self.dow_star:
            return dom
        return dom or dow  # vixie cron semantics when both are restricted

    def matches(self, t: dt.datetime) -> bool:
        return (
            t.minute in self.minutes
            and t.hour in self.hours
            and t.month in self.months
            and self._day_ok(t)
        )

    def next_after(self, after: dt.datetime) -> dt.datetime:
        """The first matching minute strictly after ``after`` (within ~5 years)."""
        t = after.replace(second=0, microsecond=0) + dt.timedelta(minutes=1)
        limit = after + dt.timedelta(days=5 * 366)
        while t < limit:
            if t.month not in self.months:
                # jump to the 1st of next month
                y, m = (t.year + (t.month // 12), t.month % 12 + 1)
                t = t.replace(year=y, month=m, day=1, hour=0, minute=0)
                continue
            if not self._day_ok(t):
                t = (t + dt.timedelta(days=1)).replace(hour=0, minute=0)
                continue
            if t.hour not in self.hours:
                t = (t + dt.timedelta(hours=1)).replace(minute=0)
                continue
            if t.minute not in self.minutes:
                t += dt.timedelta(minutes=1)
                continue
            return t
        raise ValueError("cron expression never matches")


# ── jobs ─────────────────────────────────────────────────────────────────────
@dataclass
class Job:
    name: str
    prompt: str
    every: str | None = None  # interval, e.g. "6h"
    cron: str | None = None  # 5-field cron line
    at: str | None = None  # ISO datetime, one-shot
    role: str | None = None
    model: str | None = None
    approvals: str = "ask"  # ask → sensitive calls queue in the inbox; read-only hides them
    tools: list[str] | None = None  # enabled_tools override (None = config default)
    max_iterations: int = 6
    timeout: int = 300  # wall-clock seconds for the whole run
    notify: bool = True
    enabled: bool = True
    once: bool = False  # delete after the first run (follow-ups, `at` jobs)
    parent: str | None = None  # job that scheduled this one
    created: float = field(default_factory=time.time)
    last_run: float | None = None
    next_run: float | None = None
    runs: int = 0
    last_status: str = ""
    # prompt (default) · orders (re-read ~/.oshell/orders.md each wake) ·
    # watch (fires only when the watched path changed — see oshell.watch)
    kind: str = "prompt"
    watch: dict | None = None

    def __post_init__(self) -> None:
        if not _NAME_RE.match(self.name):
            raise ValueError("job names are lowercase letters, digits, '-' and '_'")
        if self.kind not in ("prompt", "orders", "watch"):
            raise ValueError("kind must be prompt, orders or watch")
        if self.kind == "watch":
            if not self.watch:
                raise ValueError("a watch job needs a watch spec (path, pattern, event, settle)")
            watch_mod.WatchSpec.from_dict(self.watch)  # validates
            self.every = self.every or "1m"
        if not (self.every or self.cron or self.at):
            raise ValueError("a job needs a schedule: every / cron / at")
        if self.every:
            parse_interval(self.every)
        if self.cron:
            Cron.parse(self.cron)
        if self.at:
            dt.datetime.fromisoformat(self.at)
            self.once = True
        if self.approvals not in ("ask", "read-only", "auto"):
            raise ValueError("approvals must be ask, read-only or auto")

    @property
    def schedule(self) -> str:
        if self.kind == "watch" and self.watch:
            return watch_mod.WatchSpec.from_dict(self.watch).describe()
        if self.every:
            return f"every {self.every}"
        if self.cron:
            return f"cron {self.cron}"
        return f"at {self.at}"

    def compute_next(self, after: float | None = None) -> float | None:
        base = after if after is not None else time.time()
        if self.at:
            when = dt.datetime.fromisoformat(self.at).timestamp()
            return when if when > (self.last_run or 0) else None
        if self.every:
            anchor = self.last_run if self.last_run else base
            return anchor + parse_interval(self.every) if self.last_run else base
        assert self.cron
        after_dt = dt.datetime.fromtimestamp(base)
        return Cron.parse(self.cron).next_after(after_dt).timestamp()

    def is_due(self, now: float | None = None) -> bool:
        if not self.enabled:
            return False
        now = now if now is not None else time.time()
        if self.next_run is None:
            self.next_run = self.compute_next(now if not self.last_run else self.last_run)
        return self.next_run is not None and self.next_run <= now


def jobs_dir(directory: str | Path | None = None) -> Path:
    return Path(directory or DEFAULT_DIR).expanduser()


def _job_path(name: str, directory: str | Path | None = None) -> Path:
    return jobs_dir(directory) / f"{name}.json"


def save_job(job: Job, directory: str | Path | None = None) -> Path:
    d = jobs_dir(directory)
    d.mkdir(parents=True, exist_ok=True)
    p = _job_path(job.name, d)
    p.write_text(json.dumps(asdict(job), indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def load_job(name: str, directory: str | Path | None = None) -> Job | None:
    p = _job_path(name, directory)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return Job(**data)
    except (OSError, ValueError, TypeError):
        return None


def list_jobs(directory: str | Path | None = None) -> list[Job]:
    d = jobs_dir(directory)
    if not d.is_dir():
        return []
    out = [j for j in (load_job(p.stem, d) for p in sorted(d.glob("*.json"))) if j is not None]
    return sorted(out, key=lambda j: j.name)


def delete_job(name: str, directory: str | Path | None = None) -> None:
    p = _job_path(name, directory)
    if not p.is_file():
        raise FileNotFoundError(f"no job named {name}")
    p.unlink()


def add_job(job: Job, directory: str | Path | None = None, replace: bool = False) -> Job:
    if _job_path(job.name, directory).exists() and not replace:
        raise FileExistsError(f"job {job.name} exists (use --replace)")
    job.next_run = job.compute_next()
    save_job(job, directory)
    return job


def _slug_tail(path: str) -> str:
    """'~/builds/release' → 'release' (for auto-named watch jobs)."""
    tail = Path(path).expanduser().name or "path"
    return re.sub(r"[^a-z0-9_-]+", "-", tail.lower()).strip("-") or "path"


def unique_name(base: str, directory: str | Path | None = None) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", base.lower()).strip("-")[:40] or "followup"
    name, n = slug, 2
    while _job_path(name, directory).exists():
        name = f"{slug}-{n}"
        n += 1
    return name


def due_jobs(now: float | None = None, directory: str | Path | None = None) -> list[Job]:
    """Jobs to run now. Watch jobs are 'due' only when their path changed."""
    now = now if now is not None else time.time()
    out: list[Job] = []
    for j in list_jobs(directory):
        if not j.is_due(now):
            continue
        if j.kind == "watch":
            spec = watch_mod.WatchSpec.from_dict(j.watch or {})
            changes = watch_mod.check(j.name, spec, jobs_dir(directory), now)
            if not changes:
                # Nothing happened: rescan next interval; not a run.
                j.next_run = now + parse_interval(j.every or "1m")
                save_job(j, directory)
                continue
            j.pending_changes = changes  # type: ignore[attr-defined]
        out.append(j)
    return out


# ── running ──────────────────────────────────────────────────────────────────
@dataclass
class RunResult:
    job: Job
    note: inbox.Note | None
    status: str  # ok | error | skipped
    error: str = ""


class _InboxApprover:
    """The unattended approver: read-only shell commands run; everything else
    sensitive is recorded as a proposal and declined."""

    def __init__(self) -> None:
        self.proposals: list[inbox.Proposal] = []
        self.allowed: list[str] = []  # read-only commands that ran

    def __call__(self, call) -> bool:
        if call.name == "run_command":
            from .shellops import is_readonly

            command = str(call.arguments.get("command", ""))
            if is_readonly(command):
                self.allowed.append(command)
                return True
        self.proposals.append(inbox.Proposal(tool=call.name, arguments=dict(call.arguments)))
        return False


QUEUED_NOTE = (
    "[queued] this action was saved to the user's inbox for approval and did NOT run. "
    "Say what you queued and why in your report, then continue with read-only work."
)


def build_job_agent(job: Job, config: Config, *, provider=None, memory=None):
    """A fresh non-interactive Agent shaped by the job's budget and approvals."""
    from .agent import Agent
    from .memory import MemoryStore
    from .providers import get_provider
    from .tools import default_registry

    cfg = config.model_copy(deep=True)
    cfg.approvals = job.approvals
    cfg.max_tool_iterations = job.max_iterations
    if job.tools:
        cfg.enabled_tools = list(job.tools)
    provider = provider or get_provider(cfg)
    model = (
        job.model or (cfg.routing.fast_model if cfg.routing.enabled else None) or cfg.default_model
    )
    memory = memory if memory is not None else MemoryStore(cfg.memory.path)
    registry = default_registry(provider, cfg, model=model, memory=memory)
    approver = _InboxApprover()
    agent = Agent(provider, registry, cfg, model=model, memory=memory, approver=approver)
    agent.denial_text = QUEUED_NOTE
    return agent, approver


def _previous_block(job: Job, inbox_dir: str | Path | None) -> str:
    prev = inbox.latest_for_job(job.name, inbox_dir)
    if prev is None:
        return ""
    body = prev.body.strip()
    if len(body) > 1500:
        body = body[:1500] + " …"
    return f"\n### Your previous report ({prev.when})\n{body}\n"


def run_job(
    job: Job,
    config: Config,
    *,
    provider=None,
    memory=None,
    directory: str | Path | None = None,
    inbox_dir: str | Path | None = None,
    on_event=None,
) -> RunResult:
    """Run one job now: fresh agent → report → inbox note → job state."""
    global CURRENT_JOB
    from . import commands as custom
    from . import roles as roles_mod
    from .agent import LimitReached, TextDelta, ToolStarted, TurnComplete

    prompt = job.prompt
    if prompt.startswith("/"):
        head, _, rest = prompt[1:].partition(" ")
        rendered = custom.render(head, rest)
        if rendered is not None:
            prompt = rendered
    orders_now: list[orders_mod.Order] = []
    orders_state: orders_mod.State | None = None
    if job.kind == "orders":
        orders_now = orders_mod.load_orders(config.jobs.orders_path)
        orders_state = orders_mod.load_state(config.jobs.orders_state)
        if not orders_now:
            return RunResult(job=job, note=None, status="skipped", error="no standing orders")
        prompt = orders_mod.build_prompt(orders_now, orders_state)
    elif job.kind == "watch":
        changes = getattr(job, "pending_changes", None)
        if changes is None:  # run by hand: rescan so there's something to say
            spec = watch_mod.WatchSpec.from_dict(job.watch or {})
            changes = watch_mod.check(job.name, spec, jobs_dir(directory))
        spec = watch_mod.WatchSpec.from_dict(job.watch or {})
        listing = watch_mod.describe_changes(changes) if changes else "(no changes detected)"
        prompt = (
            f"{prompt}\n\nWatched path: {spec.path}\n"
            f"Files changed since the last check (settled ≥{spec.settle}s):\n{listing}"
        )
    t0 = time.monotonic()
    CURRENT_JOB = job.name
    try:
        agent, approver = build_job_agent(job, config, provider=provider, memory=memory)
        extra = SCHEDULED_RUN_PROMPT.format(
            name=job.name, schedule=job.schedule, previous=_previous_block(job, inbox_dir)
        )
        if job.role:
            role_text = roles_mod.role_prompt(job.role)
            if role_text:
                extra = f"{role_text}\n\n{extra}"
        agent.system_extra = extra
        answer, tools_used, hit_limit, timed_out = "", [], False, False
        for event in agent.send(prompt):
            if on_event is not None:
                on_event(event)
            if isinstance(event, TextDelta):
                answer += event.text
            elif isinstance(event, ToolStarted):
                tools_used.append(event.name)
            elif isinstance(event, TurnComplete):
                answer = event.text or answer
            elif isinstance(event, LimitReached):
                hit_limit = True
            if time.monotonic() - t0 > job.timeout:
                timed_out = True
                break
        body = answer.strip() or "(the model returned no report)"
        if job.kind == "orders" and orders_state is not None:
            orders_mod.apply_report(orders_now, orders_state, body)
            orders_mod.save_state(orders_state, config.jobs.orders_state)
            body = orders_mod.strip_status_block(body) or body
        if hit_limit:
            body += f"\n\n_stopped at the {job.max_iterations}-round tool budget_"
        if timed_out:
            body += f"\n\n_stopped at the {job.timeout}s time budget_"
        first = next((ln.strip("# ").strip() for ln in body.splitlines() if ln.strip()), job.name)
        title = re.sub(r"[*_`]+", "", first)[:90]  # plain text: no markdown in a title
        note = inbox.add(
            job.name,
            title,
            body,
            approver.proposals,
            directory=inbox_dir,
            tools_used=sorted(set(tools_used)),
            duration_s=time.monotonic() - t0,
        )
        status, error = "ok", ""
    except Exception as exc:  # a broken run is still a note — silence is worse
        note = inbox.add(
            job.name,
            f"{job.name} failed",
            "The scheduled run raised an error before it could report.",
            directory=inbox_dir,
            error=f"{type(exc).__name__}: {exc}",
            duration_s=time.monotonic() - t0,
        )
        status, error = "error", f"{type(exc).__name__}: {exc}"
    finally:
        CURRENT_JOB = None

    now = time.time()
    job.last_run = now
    job.runs += 1
    job.last_status = status
    if job.once:
        try:
            delete_job(job.name, directory)
        except FileNotFoundError:
            pass
    else:
        job.next_run = job.compute_next(now)
        save_job(job, directory)
    if job.notify and config.jobs.notify:
        from . import desktop

        pend = len(note.pending) if note else 0
        tail = f" · {pend} action{'s' if pend != 1 else ''} to approve" if pend else ""
        desktop.notify(f"oshell · {job.name}", (note.title if note else status) + tail)
    return RunResult(job=job, note=note, status=status, error=error)


def tick(
    config: Config,
    now: float | None = None,
    *,
    directory: str | Path | None = None,
    inbox_dir: str | Path | None = None,
    provider=None,
) -> list[RunResult]:
    """Run every due job (sequentially). What the OS scheduler calls each minute."""
    results = []
    for job in due_jobs(now, directory):
        results.append(
            run_job(job, config, provider=provider, directory=directory, inbox_dir=inbox_dir)
        )
    return results


# ── OS scheduler installation ────────────────────────────────────────────────
LAUNCHD_LABEL = "com.oshell.jobs"
SYSTEMD_UNIT = "oshell-jobs"
SCHTASK_NAME = "oshell-jobs"


def oshell_command() -> list[str]:
    """How the OS should invoke us: the `oshell` binary if on PATH, else python -m."""
    exe = shutil.which("oshell")
    if exe:
        return [exe]
    return [sys.executable, "-m", "oshell"]


def launchd_plist(cmd: list[str], log: Path, interval: int = 60) -> str:
    args = "".join(f"\n    <string>{c}</string>" for c in cmd + ["jobs", "tick"])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{LAUNCHD_LABEL}</string>
  <key>ProgramArguments</key>
  <array>{args}
  </array>
  <key>StartInterval</key><integer>{interval}</integer>
  <key>RunAtLoad</key><true/>
  <key>WorkingDirectory</key><string>{Path.home()}</string>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>{os.environ.get("PATH", "/usr/bin:/bin")}</string>
    <key>HOME</key><string>{Path.home()}</string>
  </dict>
</dict>
</plist>
"""


def systemd_units(cmd: list[str], interval: int = 60) -> tuple[str, str]:
    exec_start = " ".join(cmd + ["jobs", "tick"])
    service = f"""[Unit]
Description=oshell scheduled jobs (runs whatever is due)

[Service]
Type=oneshot
ExecStart={exec_start}
WorkingDirectory={Path.home()}
"""
    timer = f"""[Unit]
Description=Run oshell jobs every {interval}s

[Timer]
OnBootSec=60
OnUnitActiveSec={interval}
AccuracySec=15

[Install]
WantedBy=timers.target
"""
    return service, timer


def install_plan(interval: int = 60) -> tuple[str, list[list[str]], dict[Path, str]]:
    """(description, commands to run, files to write) for this platform."""
    cmd = oshell_command()
    system = platform.system()
    if system == "Darwin":
        plist = Path.home() / "Library/LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
        log = Path("~/.oshell/jobs.log").expanduser()
        files = {plist: launchd_plist(cmd, log, interval)}
        cmds = [
            ["launchctl", "bootout", f"gui/{os.getuid()}", str(plist)],
            ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist)],
        ]
        return f"launchd agent {LAUNCHD_LABEL} (every {interval}s)", cmds, files
    if system == "Windows":
        tr = " ".join(f'"{c}"' if " " in c else c for c in cmd + ["jobs", "tick"])
        cmds = [
            [
                "schtasks",
                "/Create",
                "/F",
                "/SC",
                "MINUTE",
                "/MO",
                "1",
                "/TN",
                SCHTASK_NAME,
                "/TR",
                tr,
            ]
        ]
        return f"Task Scheduler task {SCHTASK_NAME} (every minute)", cmds, {}
    unit_dir = Path.home() / ".config/systemd/user"
    service, timer = systemd_units(cmd, interval)
    files = {
        unit_dir / f"{SYSTEMD_UNIT}.service": service,
        unit_dir / f"{SYSTEMD_UNIT}.timer": timer,
    }
    cmds = [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", f"{SYSTEMD_UNIT}.timer"],
    ]
    return f"systemd user timer {SYSTEMD_UNIT}.timer (every {interval}s)", cmds, files


def install(interval: int = 60, dry_run: bool = False) -> str:
    desc, cmds, files = install_plan(interval)
    if dry_run:
        return desc
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    errors = []
    for i, c in enumerate(cmds):
        r = subprocess.run(c, capture_output=True, text=True)
        # launchctl bootout fails harmlessly when nothing was loaded yet.
        if r.returncode != 0 and not (platform.system() == "Darwin" and i == 0):
            errors.append((r.stderr or r.stdout).strip())
    if errors:
        raise RuntimeError("; ".join(errors))
    return desc


def uninstall() -> str:
    system = platform.system()
    if system == "Darwin":
        plist = Path.home() / "Library/LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
        subprocess.run(
            ["launchctl", "bootout", f"gui/{os.getuid()}", str(plist)], capture_output=True
        )
        plist.unlink(missing_ok=True)
        return f"removed {LAUNCHD_LABEL}"
    if system == "Windows":
        subprocess.run(["schtasks", "/Delete", "/F", "/TN", SCHTASK_NAME], capture_output=True)
        return f"removed {SCHTASK_NAME}"
    subprocess.run(
        ["systemctl", "--user", "disable", "--now", f"{SYSTEMD_UNIT}.timer"], capture_output=True
    )
    unit_dir = Path.home() / ".config/systemd/user"
    for f in (f"{SYSTEMD_UNIT}.service", f"{SYSTEMD_UNIT}.timer"):
        (unit_dir / f).unlink(missing_ok=True)
    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
    return f"removed {SYSTEMD_UNIT}"


def installed() -> bool:
    system = platform.system()
    if system == "Darwin":
        return (Path.home() / "Library/LaunchAgents" / f"{LAUNCHD_LABEL}.plist").is_file()
    if system == "Windows":
        r = subprocess.run(["schtasks", "/Query", "/TN", SCHTASK_NAME], capture_output=True)
        return r.returncode == 0
    return (Path.home() / ".config/systemd/user" / f"{SYSTEMD_UNIT}.timer").is_file()


def describe_when(ts: float | None) -> str:
    if ts is None:
        return "—"
    delta = ts - time.time()
    when = time.strftime("%m-%d %H:%M", time.localtime(ts))
    if abs(delta) < 60:
        rel = "now"
    elif delta > 0:
        rel = "in " + _humanize(delta)
    else:
        rel = _humanize(-delta) + " ago"
    return f"{when} ({rel})"


def _humanize(secs: float) -> str:
    secs = int(secs)
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h {secs % 3600 // 60}m"
    return f"{secs // 86400}d {secs % 86400 // 3600}h"
