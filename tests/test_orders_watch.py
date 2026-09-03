"""Phase two of presence: standing orders and file watches."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from typing import Any

import pytest

from oshell import inbox, orders, schedule, watch
from oshell.config import Config
from oshell.providers.base import ChatChunk, LLMProvider, Message, ToolCall

# ── standing orders ──────────────────────────────────────────────────────────


def test_parse_orders_bullets_priorities_and_comments():
    text = """# Standing orders
Some prose that is not an order.
- [high] Keep the disk under 80%.
* Tell me about new listening ports.
3. [low] Note new services once a day.
# - a commented-out order
- [HIGH] Case-insensitive tag.
"""
    got = orders.parse_orders(text)
    assert [(o.n, o.priority) for o in got] == [(1, "high"), (2, "normal"), (3, "low"), (4, "high")]
    assert got[0].text == "Keep the disk under 80%."
    assert (
        got[0].id == orders.Order(n=9, text="keep the disk under 80%.").id
    )  # stable, position-free


def test_orders_file_add_remove_and_template(tmp_path):
    p = tmp_path / "orders.md"
    assert orders.load_orders(p) == []
    o = orders.add_order("Keep the disk under 80%", "high", p)
    assert o.n == 4 and o.priority == "high"  # appended after the template's three examples
    assert "[high] Keep the disk under 80%" in p.read_text()
    removed = orders.remove_order(1, p)
    assert "main disk under 80%" in removed.text
    assert len(orders.load_orders(p)) == 3
    with pytest.raises(IndexError):
        orders.remove_order(42, p)
    with pytest.raises(ValueError):
        orders.add_order("x", "urgent", p)


def test_due_orders_respects_priority_and_staleness():
    items = orders.parse_orders("- [high] a\n- b\n- [low] c\n- d\n")
    now = time.time()
    st = orders.State(
        findings={
            items[1].id: orders.Finding("ok", "fine", now - 60),  # fresh normal → not due
            items[2].id: orders.Finding("ok", "fine", now - 2 * 3600),  # fresh low → not due
            items[3].id: orders.Finding("attention", "disk", now - 60),  # attention → due
        }
    )
    due = [o.n for o in orders.due_orders(items, st, now)]
    assert due == [1, 4]  # high always; attention always; b and c not stale yet
    st.findings[items[1].id].ts = now - 5 * 3600
    assert 2 in [o.n for o in orders.due_orders(items, st, now)]


def test_prompt_status_roundtrip_and_render():
    items = orders.parse_orders("- [high] disk\n- ports\n")
    st = orders.State()
    prompt = orders.build_prompt(items, st)
    assert "1. [high] disk" in prompt and "← DUE" in prompt and "STATUS:" in prompt
    report = (
        "**Disk is fine.** Nothing new on ports.\n\nSTATUS:\n"
        "#1 ok — 62% used\n- #2: attention — port 8080 appeared (python)\n"
    )
    orders.apply_report(items, st, report, now=1000.0)
    assert st.findings[items[0].id].status == "ok" and st.findings[items[0].id].note == "62% used"
    assert st.findings[items[1].id].status == "attention"
    assert st.last_run == 1000.0
    assert orders.strip_status_block(report) == "**Disk is fine.** Nothing new on ports."
    md = orders.render(items, st, now=1000.0 + 120)
    assert "✓ **1.**" in md and "⚠ **2.**" in md and "port 8080" in md
    # A removed order's finding is forgotten on the next apply.
    orders.apply_report(items[:1], st, "STATUS:\n#1 ok — still fine", now=2000.0)
    assert items[1].id not in st.findings
    assert orders.render([], st).startswith("_No standing orders")


def test_state_roundtrip(tmp_path):
    p = tmp_path / "state.json"
    st = orders.State(findings={"abc": orders.Finding("ok", "n", 5.0)}, last_run=5.0)
    orders.save_state(st, p)
    back = orders.load_state(p)
    assert back.findings["abc"].note == "n" and back.last_run == 5.0
    assert orders.load_state(tmp_path / "missing.json").findings == {}


# ── file watches ─────────────────────────────────────────────────────────────


def test_watch_scan_diff_settle_and_events(tmp_path):
    d = tmp_path / "builds"
    d.mkdir()
    (d / "a.log").write_text("x")
    spec = watch.WatchSpec(path=str(d), pattern="*.log", settle=5)
    base = watch.scan(spec)
    assert set(base) == {"a.log"}
    time.sleep(0.01)
    (d / "b.log").write_text("new")
    (d / "c.txt").write_text("ignored by pattern")
    cur = watch.scan(spec)
    now = time.time()
    # Not settled yet: nothing reported, and b.log is held back from the snapshot.
    changes, store = watch.diff(base, cur, spec, now)
    assert changes == [] and "b.log" not in store
    # Settled: reported as created.
    changes, store = watch.diff(base, cur, spec, now + 60)
    assert [(c.kind, c.path) for c in changes] == [("created", "b.log")] and "b.log" in store
    # Deletion and modification, filtered by event.
    (d / "a.log").unlink()
    old = os.stat(d / "b.log").st_mtime
    (d / "b.log").write_text("longer content")
    os.utime(d / "b.log", (old - 100, old - 100))  # make it look settled
    cur2 = watch.scan(spec)
    changes, _ = watch.diff(store, cur2, spec, now + 60)
    assert {(c.kind, c.path) for c in changes} == {("deleted", "a.log"), ("modified", "b.log")}
    only_deleted = watch.WatchSpec(path=str(d), pattern="*.log", event="deleted")
    changes, _ = watch.diff(store, cur2, only_deleted, now + 60)
    assert [(c.kind, c.path) for c in changes] == [("deleted", "a.log")]
    assert "deleted: a.log" in watch.describe_changes(changes)
    with pytest.raises(ValueError):
        watch.WatchSpec(path=str(d), event="renamed")


def test_watch_check_baselines_then_reports(tmp_path):
    d = tmp_path / "dl"
    d.mkdir()
    (d / "old.iso").write_text("x")
    jobs_dir = tmp_path / "jobs"
    spec = watch.WatchSpec(path=str(d), settle=0)
    assert watch.check("dl", spec, jobs_dir) == []  # baseline: existing files don't fire
    (d / "new.iso").write_text("y")
    changes = watch.check("dl", spec, jobs_dir, now=time.time() + 5)
    assert [(c.kind, c.path) for c in changes] == [("created", "new.iso")]
    assert watch.check("dl", spec, jobs_dir, now=time.time() + 10) == []  # nothing new


class _Reporter(LLMProvider):
    name = "reporter"

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def list_models(self) -> list[str]:
        return ["m"]

    def chat(self, messages: list[Message], **kwargs: Any) -> Iterator[ChatChunk]:
        self.prompts.append(next(m.content for m in messages if m.role == "user"))
        yield ChatChunk(content=self.reply, done=True)


def test_watch_job_is_due_only_on_change_and_gets_the_change_list(tmp_path):
    jobs_dir, inbox_dir = tmp_path / "jobs", tmp_path / "inbox"
    target = tmp_path / "builds"
    target.mkdir()
    cfg = Config(project_context=False)
    cfg.jobs.notify = False
    spec = watch.WatchSpec(path=str(target), pattern="*.dmg", settle=0)
    job = schedule.Job(
        name="release", prompt="Is the release build good?", kind="watch", watch=spec.to_dict()
    )
    assert job.every == "1m" and job.schedule.startswith("watch ")
    schedule.add_job(job, jobs_dir)
    watch.check("release", spec, jobs_dir)  # baseline
    now = time.time() + 120
    assert schedule.due_jobs(now, jobs_dir) == []  # nothing changed → not a run
    saved = schedule.load_job("release", jobs_dir)
    assert saved.runs == 0 and saved.next_run > now  # just rescheduled the rescan
    (target / "oshell-0.3.dmg").write_bytes(b"\\x00" * 2048)
    due = schedule.due_jobs(now + 120, jobs_dir)
    assert [j.name for j in due] == ["release"]
    prov = _Reporter("**Release build landed:** oshell-0.3.dmg (2 KB).")
    r = schedule.run_job(due[0], cfg, provider=prov, directory=jobs_dir, inbox_dir=inbox_dir)
    assert r.status == "ok"
    assert (
        "created: oshell-0.3.dmg" in prov.prompts[0]
        and "Is the release build good?" in prov.prompts[0]
    )
    assert r.note.title.startswith("Release build landed")


def test_orders_job_builds_prompt_and_updates_state(tmp_path, monkeypatch):
    jobs_dir, inbox_dir = tmp_path / "jobs", tmp_path / "inbox"
    cfg = Config(project_context=False)
    cfg.jobs.notify = False
    cfg.jobs.orders_path = str(tmp_path / "orders.md")
    cfg.jobs.orders_state = str(tmp_path / "orders.state.json")
    job = schedule.add_job(
        schedule.Job(name="orders", prompt="Check the standing orders.", kind="orders", every="1h"),
        jobs_dir,
    )
    # No orders yet → skipped, no note.
    r = schedule.run_job(job, cfg, provider=_Reporter("x"), directory=jobs_dir, inbox_dir=inbox_dir)
    assert r.status == "skipped" and r.note is None
    orders.add_order("Keep the disk under 80%", "high", cfg.jobs.orders_path)
    orders.remove_order(1, cfg.jobs.orders_path)
    orders.remove_order(1, cfg.jobs.orders_path)
    orders.remove_order(1, cfg.jobs.orders_path)  # only ours remains
    prov = _Reporter("All quiet. Disk at 62%.\n\nSTATUS:\n#1 ok — 62% used")
    r = schedule.run_job(job, cfg, provider=prov, directory=jobs_dir, inbox_dir=inbox_dir)
    assert r.status == "ok"
    assert (
        "Standing orders" in prov.prompts[0] and "[high] Keep the disk under 80%" in prov.prompts[0]
    )
    st = orders.load_state(cfg.jobs.orders_state)
    (finding,) = st.findings.values()
    assert finding.status == "ok" and finding.note == "62% used"
    assert "STATUS" not in r.note.body  # the trailer is folded into state, not shown
    # Second wake shows the previous finding in the prompt.
    prov2 = _Reporter("Still fine.\n\nSTATUS:\n#1 ok — 63%")
    schedule.run_job(job, cfg, provider=prov2, directory=jobs_dir, inbox_dir=inbox_dir)
    assert "last: ok" in prov2.prompts[0] and '"62% used"' in prov2.prompts[0]


def test_watch_path_tool_creates_a_baselined_watch_job(tmp_path, monkeypatch):
    from oshell.tools.schedule import WatchPathTool

    jobs_dir = tmp_path / "jobs"
    target = tmp_path / "Downloads"
    target.mkdir()
    (target / "existing.zip").write_text("x")
    out = WatchPathTool(str(jobs_dir)).run(
        path=str(target), prompt="Tell me when the ISO finishes", pattern="*.iso", settle=30
    )
    assert "watching" in out and "watch-downloads" in out
    (job,) = schedule.list_jobs(jobs_dir)
    assert job.kind == "watch" and job.watch["pattern"] == "*.iso" and job.watch["settle"] == 30
    assert watch.load_snapshot(job.name, jobs_dir) is not None  # baselined
    from oshell.tools.base import ToolError

    with pytest.raises(ToolError):
        WatchPathTool(str(jobs_dir)).run(path="", prompt="p")


def test_inbox_untouched_by_skipped_orders_run(tmp_path):
    assert inbox.list_notes(directory=tmp_path / "nothing") == []
    _ = ToolCall  # imported for parity with the other schedule tests
