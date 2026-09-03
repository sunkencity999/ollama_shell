"""Scheduling tools — the model can plan a check-in, not just answer.

``schedule_followup`` creates a job (one-shot by default, recurring with
``every``) that wakes a fresh agent later with the given prompt and this
run's report as context. The user sees the result in their inbox. Scheduling
itself is not gated — the user chose that — because whatever the follow-up
does is still subject to the same approvals as any other run.
"""

from __future__ import annotations

import datetime as dt
import time
from typing import Any

from .. import schedule
from .base import Tool, ToolError


class ScheduleFollowupTool(Tool):
    name = "schedule_followup"
    description = (
        "Schedule a later check-in: a fresh run of yourself with PROMPT, after DELAY "
        "(e.g. '30m', '2h', '1d'), or AT an ISO time, or repeating EVERY interval. Use it "
        "to watch a build/download/metric, to re-check something that was still in "
        "progress, or to set up a recurring watch the user asked for. The result lands "
        "in the user's inbox. Don't schedule more than one follow-up per turn."
    )
    local_only = True
    parameters = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "What the follow-up run should do"},
            "delay": {"type": "string", "description": "Run once after this long: 30m, 2h, 1d"},
            "at": {"type": "string", "description": "Run once at this ISO datetime"},
            "every": {"type": "string", "description": "Repeat at this interval: 15m, 6h, 1d"},
            "name": {"type": "string", "description": "Optional short name (lowercase, dashes)"},
        },
        "required": ["prompt"],
    }

    def __init__(self, directory: str | None = None):
        self._dir = directory

    def run(
        self,
        prompt: str = "",
        delay: str | None = None,
        at: str | None = None,
        every: str | None = None,
        name: str | None = None,
        **_: Any,
    ) -> str:
        if not prompt.strip():
            raise ToolError("the follow-up needs a prompt")
        if not (delay or at or every):
            raise ToolError("give delay ('30m'), at (ISO time) or every ('6h')")
        kwargs: dict[str, Any] = {}
        if every:
            kwargs["every"] = every
        elif at:
            try:
                dt.datetime.fromisoformat(at)
            except ValueError as exc:
                raise ToolError(f"bad ISO datetime {at!r}") from exc
            kwargs["at"] = at
        else:
            secs = schedule.parse_interval(delay or "")
            kwargs["at"] = dt.datetime.fromtimestamp(time.time() + secs).isoformat(
                timespec="seconds"
            )
        base = name or (f"{schedule.CURRENT_JOB}-followup" if schedule.CURRENT_JOB else prompt[:24])
        job_name = schedule.unique_name(base, self._dir)
        try:
            job = schedule.Job(
                name=job_name, prompt=prompt.strip(), parent=schedule.CURRENT_JOB, **kwargs
            )
            schedule.add_job(job, self._dir)
        except (ValueError, FileExistsError) as exc:
            raise ToolError(str(exc)) from exc
        when = schedule.describe_when(job.next_run)
        return (
            f"scheduled {job.name} ({job.schedule}) → next run {when}. "
            "The user will see its report in their inbox (oshell inbox)."
        )


class ListJobsTool(Tool):
    name = "list_jobs"
    description = "List the user's scheduled jobs (name, schedule, next run, last status)."
    local_only = True
    parameters = {"type": "object", "properties": {}}

    def __init__(self, directory: str | None = None):
        self._dir = directory

    def run(self, **_: Any) -> str:
        jobs = schedule.list_jobs(self._dir)
        if not jobs:
            return "no scheduled jobs"
        lines = []
        for j in jobs:
            flag = "" if j.enabled else " (disabled)"
            lines.append(
                f"{j.name}{flag}: {j.schedule} · next {schedule.describe_when(j.next_run)} · "
                f"runs {j.runs}{' · ' + j.last_status if j.last_status else ''} — {j.prompt[:80]}"
            )
        return "\n".join(lines)


class CancelJobTool(Tool):
    name = "cancel_job"
    description = "Cancel (delete) a scheduled job by name. Use list_jobs to see names."
    local_only = True
    parameters = {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "The job's name"}},
        "required": ["name"],
    }

    def __init__(self, directory: str | None = None):
        self._dir = directory

    def run(self, name: str = "", **_: Any) -> str:
        try:
            schedule.delete_job(name, self._dir)
        except FileNotFoundError as exc:
            raise ToolError(str(exc)) from exc
        return f"cancelled {name}"


def schedule_tools(directory: str | None = None) -> list[Tool]:
    return [ScheduleFollowupTool(directory), ListJobsTool(directory), CancelJobTool(directory)]
