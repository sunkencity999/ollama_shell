"""Scheduled runs + inbox: schedules, the job store, unattended runs, follow-ups."""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Iterator
from typing import Any

import pytest

from oshell import inbox, schedule
from oshell.config import Config
from oshell.providers.base import ChatChunk, LLMProvider, Message, ToolCall

# ── schedules ────────────────────────────────────────────────────────────────


def test_interval_parsing():
    assert schedule.parse_interval("30s") == 30
    assert schedule.parse_interval("15m") == 900
    assert schedule.parse_interval("6h") == 21600
    assert schedule.parse_interval(" 1d ") == 86400
    for bad in ("", "fast", "0m", "5w"):
        with pytest.raises(ValueError):
            schedule.parse_interval(bad)


def test_cron_next_after_handles_common_shapes():
    c = schedule.Cron.parse("0 9 * * 1-5")  # weekdays at 09:00
    friday_10 = dt.datetime(2026, 9, 4, 10, 0)  # a Friday
    nxt = c.next_after(friday_10)
    assert nxt == dt.datetime(2026, 9, 7, 9, 0)  # skips the weekend to Monday
    every15 = schedule.Cron.parse("*/15 * * * *")
    assert every15.next_after(dt.datetime(2026, 1, 1, 10, 7)) == dt.datetime(2026, 1, 1, 10, 15)
    first_of_month = schedule.Cron.parse("30 6 1 * *")
    assert first_of_month.next_after(dt.datetime(2026, 1, 20)) == dt.datetime(2026, 2, 1, 6, 30)
    sunday7 = schedule.Cron.parse("0 0 * * 7")  # 7 == Sunday
    assert sunday7.next_after(dt.datetime(2026, 9, 2)).weekday() == 6
    with pytest.raises(ValueError):
        schedule.Cron.parse("0 9 * *")
    with pytest.raises(ValueError):
        schedule.Cron.parse("61 * * * *")


def test_job_validation_and_next_run(tmp_path):
    with pytest.raises(ValueError, match="schedule"):
        schedule.Job(name="x", prompt="p")
    with pytest.raises(ValueError, match="names"):
        schedule.Job(name="Bad Name", prompt="p", every="1h")
    j = schedule.Job(name="disk", prompt="check disk", every="6h")
    assert j.schedule == "every 6h"
    now = time.time()
    assert abs(j.compute_next(now) - now) < 1  # first run: as soon as the tick sees it
    j.last_run = now
    assert abs(j.compute_next(now) - (now + 21600)) < 1
    one = schedule.Job(name="once", prompt="p", at="2030-01-01T09:00:00")
    assert one.once and one.schedule.startswith("at ")


def test_job_store_roundtrip_and_due(tmp_path):
    d = tmp_path / "jobs"
    j = schedule.add_job(schedule.Job(name="disk", prompt="check disk", every="6h"), d)
    assert schedule.load_job("disk", d).prompt == "check disk"
    assert [x.name for x in schedule.list_jobs(d)] == ["disk"]
    with pytest.raises(FileExistsError):
        schedule.add_job(schedule.Job(name="disk", prompt="again", every="1h"), d)
    assert j.is_due(time.time() + 1)
    j.enabled = False
    assert not j.is_due()
    assert schedule.unique_name("disk", d) == "disk-2"
    schedule.delete_job("disk", d)
    assert schedule.list_jobs(d) == []
    with pytest.raises(FileNotFoundError):
        schedule.delete_job("disk", d)


# ── inbox ────────────────────────────────────────────────────────────────────


def test_inbox_notes_and_proposals(tmp_path):
    d = tmp_path / "inbox"
    assert inbox.list_notes(directory=d) == [] and inbox.unread_count(d) == 0
    n = inbox.add(
        "disk",
        "Disk at 91%",
        "The disk is filling up.",
        [inbox.Proposal("run_command", {"command": "docker system prune -f"})],
        directory=d,
    )
    assert n.status == "unread" and n.pending and n.id.endswith("-disk")
    assert inbox.unread_count(d) == 1 and inbox.pending_count(d) == 1
    assert inbox.get(n.id[:9], d).id == n.id  # unique prefix lookup
    md = inbox.render_markdown(n)
    assert "Disk at 91%" in md and "docker system prune -f" in md and "nothing ran" in md
    inbox.mark(n.id, "read", d)
    assert inbox.unread_count(d) == 0
    assert inbox.latest_for_job("disk", d).id == n.id
    assert inbox.clear(d) == 0  # pending proposals are kept
    assert inbox.clear(d, keep_pending=False) == 1


# ── unattended runs ──────────────────────────────────────────────────────────


class _Reporter(LLMProvider):
    """Round 1: tries a shell command + schedules a follow-up. Round 2: reports."""

    name = "reporter"

    def __init__(self) -> None:
        self.rounds = 0
        self.seen_system = ""

    def list_models(self) -> list[str]:
        return ["m"]

    def chat(self, messages: list[Message], **kwargs: Any) -> Iterator[ChatChunk]:
        self.rounds += 1
        self.seen_system = messages[0].content
        if self.rounds == 1:
            yield ChatChunk(
                content="",
                tool_calls=[
                    ToolCall(name="run_command", arguments={"command": "echo build-ok"}),
                    ToolCall(name="run_command", arguments={"command": "rm -rf /tmp/build"}),
                    ToolCall(
                        name="schedule_followup",
                        arguments={"prompt": "is the build done yet?", "delay": "30m"},
                    ),
                ],
                done=True,
            )
            return
        tool_msgs = [m.content for m in messages if m.role == "tool"]
        assert any("[queued]" in t for t in tool_msgs), tool_msgs
        assert any("build-ok" in t for t in tool_msgs), tool_msgs  # read-only ran
        yield ChatChunk(
            content="**Build dir is stale.** Queued a cleanup for approval; checking again in 30m.",
            done=True,
        )


def test_run_job_queues_sensitive_calls_and_schedules_followup(tmp_path, monkeypatch):
    jobs_dir, inbox_dir = tmp_path / "jobs", tmp_path / "inbox"
    cfg = Config(project_context=False)
    cfg.jobs.dir = str(jobs_dir)
    cfg.jobs.inbox_dir = str(inbox_dir)
    cfg.jobs.notify = False
    monkeypatch.setattr("oshell.tools.schedule.schedule.DEFAULT_DIR", str(jobs_dir))
    job = schedule.add_job(
        schedule.Job(name="build-watch", prompt="check the build", every="1h", role="sysadmin"),
        jobs_dir,
    )
    prov = _Reporter()
    result = schedule.run_job(job, cfg, provider=prov, directory=jobs_dir, inbox_dir=inbox_dir)
    assert result.status == "ok", result.error
    # The system prompt carried the role and the unattended-run instructions.
    assert "Scheduled run" in prov.seen_system and "systems administrator" in prov.seen_system
    # The read-only command ran; the mutating one did NOT — it's a proposal.
    note = result.note
    assert note.job == "build-watch" and note.title.startswith("Build dir is stale")
    assert [p.summary for p in note.pending] == ["rm -rf /tmp/build"]
    assert "run_command" in note.tools_used and "schedule_followup" in note.tools_used
    # The follow-up exists as a one-shot child job ~30m out.
    kids = [j for j in schedule.list_jobs(jobs_dir) if j.parent == "build-watch"]
    assert len(kids) == 1 and kids[0].once and kids[0].prompt == "is the build done yet?"
    assert 29 * 60 < kids[0].next_run - time.time() <= 30 * 60
    # Job state advanced and the next run is an hour out.
    saved = schedule.load_job("build-watch", jobs_dir)
    assert saved.runs == 1 and saved.last_status == "ok"
    assert 3500 < saved.next_run - time.time() <= 3600
    # A second run sees its previous report.
    prov2 = _Reporter()
    schedule.run_job(saved, cfg, provider=prov2, directory=jobs_dir, inbox_dir=inbox_dir)
    assert "Your previous report" in prov2.seen_system and "Build dir is stale" in prov2.seen_system


class _Quiet(LLMProvider):
    name = "quiet"

    def list_models(self) -> list[str]:
        return ["m"]

    def chat(self, messages: list[Message], **kwargs: Any) -> Iterator[ChatChunk]:
        yield ChatChunk(content="Nothing changed.", done=True)


def test_one_shot_jobs_delete_themselves_and_tick_runs_only_due(tmp_path):
    jobs_dir, inbox_dir = tmp_path / "jobs", tmp_path / "inbox"
    cfg = Config(project_context=False)
    cfg.jobs.notify = False
    soon = dt.datetime.now() + dt.timedelta(seconds=1)
    later = dt.datetime.now() + dt.timedelta(days=1)
    schedule.add_job(schedule.Job(name="soon", prompt="p", at=soon.isoformat()), jobs_dir)
    schedule.add_job(schedule.Job(name="later", prompt="p", at=later.isoformat()), jobs_dir)
    results = schedule.tick(
        cfg, now=time.time() + 5, directory=jobs_dir, inbox_dir=inbox_dir, provider=_Quiet()
    )
    assert [r.job.name for r in results] == ["soon"]
    assert [j.name for j in schedule.list_jobs(jobs_dir)] == ["later"]  # one-shot removed
    assert inbox.list_notes(directory=inbox_dir)[0].title == "Nothing changed."


class _Broken(LLMProvider):
    name = "broken"

    def list_models(self) -> list[str]:
        return ["m"]

    def chat(self, messages: list[Message], **kwargs: Any) -> Iterator[ChatChunk]:
        raise RuntimeError("backend down")


def test_failed_run_still_files_a_note(tmp_path):
    jobs_dir, inbox_dir = tmp_path / "jobs", tmp_path / "inbox"
    cfg = Config(project_context=False)
    cfg.jobs.notify = False
    job = schedule.add_job(schedule.Job(name="x", prompt="p", every="1h"), jobs_dir)
    r = schedule.run_job(job, cfg, provider=_Broken(), directory=jobs_dir, inbox_dir=inbox_dir)
    assert r.status == "error" and "backend down" in r.error
    assert r.note.error and schedule.load_job("x", jobs_dir).last_status == "error"


# ── OS scheduler plans ───────────────────────────────────────────────────────


def test_install_plans_are_well_formed(monkeypatch):
    monkeypatch.setattr(schedule, "oshell_command", lambda: ["/usr/local/bin/oshell"])
    monkeypatch.setattr(schedule.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(schedule.os, "getuid", lambda: 501, raising=False)
    desc, cmds, files = schedule.install_plan(60)
    assert "launchd" in desc and any("bootstrap" in c for c in cmds)
    (plist_path, plist), = files.items()
    assert plist_path.name == "com.oshell.jobs.plist"
    assert "<string>jobs</string>" in plist and "<string>tick</string>" in plist
    assert "<integer>60</integer>" in plist
    monkeypatch.setattr(schedule.platform, "system", lambda: "Linux")
    desc, cmds, files = schedule.install_plan(120)
    assert "systemd" in desc and len(files) == 2
    timer = next(t for p, t in files.items() if p.suffix == ".timer")
    assert "OnUnitActiveSec=120" in timer
    monkeypatch.setattr(schedule.platform, "system", lambda: "Windows")
    desc, cmds, files = schedule.install_plan()
    assert "schtasks" in cmds[0][0] and files == {}
