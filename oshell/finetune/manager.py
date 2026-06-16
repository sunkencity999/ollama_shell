"""Fine-tuning job manager: create, persist, list, launch, and inspect jobs.

Each job is a directory under ``config.finetune.jobs_dir`` containing the
prepared dataset, a ``job.json`` metadata file, the LoRA ``adapters/``, and a
``train.log``. Metadata is plain JSON so jobs survive restarts and can be
inspected by hand.
"""

from __future__ import annotations

import json
import os
import signal
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import Config
from .datasets import prepare_dataset
from .hardware import detect_hardware
from .mlx_runner import build_mlx_command, launch


@dataclass
class Job:
    id: str
    name: str
    base_model: str
    status: str  # prepared | running | completed | failed
    dataset_dir: str
    adapter_dir: str
    log_file: str
    job_dir: str
    params: dict[str, Any] = field(default_factory=dict)
    pid: int | None = None
    created_at: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Job:
        return cls(**d)


class FineTuneError(RuntimeError):
    pass


class FineTuneManager:
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.root = Path(self.config.finetune.jobs_dir).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    # ── job lifecycle ────────────────────────────────────────────────────────
    def create_job(
        self,
        name: str,
        base_model: str,
        dataset_path: str,
        params: dict[str, Any] | None = None,
        framework: str = "mlx",
    ) -> Job:
        """Prepare the dataset and register a job (status='prepared')."""
        job_id = f"{_slug(name)}-{uuid.uuid4().hex[:8]}"
        job_dir = self.root / job_id
        dataset_dir = job_dir / "data"
        prepare_dataset(dataset_path, str(dataset_dir), framework)

        ft = self.config.finetune
        job = Job(
            id=job_id,
            name=name,
            base_model=base_model,
            status="prepared",
            dataset_dir=str(dataset_dir),
            adapter_dir=str(job_dir / "adapters"),
            log_file=str(job_dir / "train.log"),
            job_dir=str(job_dir),
            params={
                "batch_size": ft.batch_size,
                "iters": ft.iters,
                "learning_rate": ft.learning_rate,
                "num_layers": ft.num_layers,
                **(params or {}),
            },
            created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        self._save(job)
        return job

    def start_job(self, job: Job) -> Job:
        """Launch MLX training for a prepared job."""
        hw = detect_hardware()
        if hw.framework != "mlx":
            raise FineTuneError(
                f"MLX training needs Apple Silicon; detected '{hw.platform}'. "
                "Unsloth (NVIDIA) is not wired into this runner yet."
            )
        cmd = build_mlx_command(
            model=job.base_model,
            data_dir=job.dataset_dir,
            adapter_dir=job.adapter_dir,
            batch_size=job.params["batch_size"],
            iters=job.params["iters"],
            learning_rate=job.params["learning_rate"],
            num_layers=job.params["num_layers"],
        )
        job.pid = launch(cmd, job.log_file)
        job.status = "running"
        self._save(job)
        return job

    def refresh_status(self, job: Job) -> Job:
        """Update a running job's status by checking its process and log."""
        if job.status == "running" and job.pid is not None and _process_done(job.pid):
            tail = _log_tail(job.log_file).lower()
            job.status = "failed" if ("error" in tail or "traceback" in tail) else "completed"
            self._save(job)
        return job

    # ── queries / persistence ─────────────────────────────────────────────────
    def list_jobs(self) -> list[Job]:
        jobs = []
        for meta in sorted(self.root.glob("*/job.json")):
            jobs.append(Job.from_dict(json.loads(meta.read_text(encoding="utf-8"))))
        return jobs

    def get_job(self, job_id: str) -> Job:
        meta = self.root / job_id / "job.json"
        if not meta.is_file():
            raise FineTuneError(f"no such job: {job_id}")
        return Job.from_dict(json.loads(meta.read_text(encoding="utf-8")))

    def _save(self, job: Job) -> None:
        Path(job.job_dir).mkdir(parents=True, exist_ok=True)
        (Path(job.job_dir) / "job.json").write_text(job.to_json(), encoding="utf-8")


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-") or "job"


def _process_done(pid: int) -> bool:
    """Has the process exited? Reaps our own children (so they don't linger as
    zombies); for processes we don't own, falls back to a liveness signal."""
    try:
        reaped, _ = os.waitpid(pid, os.WNOHANG)
        return reaped == pid  # nonzero => it exited and we just reaped it
    except ChildProcessError:
        # Not our child (e.g. status checked from a different invocation).
        try:
            os.kill(pid, 0)
            return False
        except OSError:
            return True
    except OSError:  # pragma: no cover - defensive
        return True


def _log_tail(path: str, n: int = 4000) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8", errors="replace")[-n:] if p.is_file() else ""


# Re-exported for callers that want to terminate a runaway job.
def stop_pid(pid: int) -> None:  # pragma: no cover - thin os wrapper
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
