"""Fine-tuning tests: hardware, dataset prep, MLX command, job manager.

Everything except the actual MLX training subprocess is covered. The subprocess
launch is exercised with a trivial fake command so no model is downloaded.
"""

from __future__ import annotations

import json

import pytest

from oshell.config import Config, FinetuneConfig
from oshell.finetune import detect_hardware, prepare_dataset
from oshell.finetune.datasets import DatasetError
from oshell.finetune.manager import FineTuneManager
from oshell.finetune.mlx_runner import build_mlx_command


# ── hardware ────────────────────────────────────────────────────────────────
def test_detect_hardware_runs_and_is_consistent():
    hw = detect_hardware()
    assert hw.framework in ("mlx", "unsloth", "cpu")
    assert hw.can_train == (hw.framework in ("mlx", "unsloth"))


# ── dataset preparation ───────────────────────────────────────────────────---
def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_prepare_jsonl_text(tmp_path):
    src = tmp_path / "d.jsonl"
    src.write_text('{"text": "one"}\n{"text": "two"}\n')
    prepare_dataset(str(src), str(tmp_path / "out"))
    rows = _read_jsonl(tmp_path / "out" / "train.jsonl")
    rows += _read_jsonl(tmp_path / "out" / "valid.jsonl")
    assert {r["text"] for r in rows} == {"one", "two"}


def test_prepare_prompt_completion(tmp_path):
    src = tmp_path / "d.jsonl"
    src.write_text('{"prompt": "Q?", "completion": "A."}\n')
    prepare_dataset(str(src), str(tmp_path / "o"))
    rows = _read_jsonl(tmp_path / "o" / "train.jsonl")
    assert "Q?" in rows[0]["text"] and "A." in rows[0]["text"]


def test_prepare_chat_messages(tmp_path):
    src = tmp_path / "d.json"
    src.write_text(json.dumps([{"messages": [
        {"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}
    ]}]))
    prepare_dataset(str(src), str(tmp_path / "o"))
    text = _read_jsonl(tmp_path / "o" / "train.jsonl")[0]["text"]
    assert "user: hi" in text and "assistant: hello" in text


def test_prepare_csv(tmp_path):
    src = tmp_path / "d.csv"
    src.write_text("text\nrow one\nrow two\n")
    prepare_dataset(str(src), str(tmp_path / "o"))
    texts = {r["text"] for r in _read_jsonl(tmp_path / "o" / "train.jsonl")
             + _read_jsonl(tmp_path / "o" / "valid.jsonl")}
    assert "row one" in texts and "row two" in texts


def test_prepare_txt(tmp_path):
    src = tmp_path / "d.txt"
    src.write_text("alpha\n\nbeta\n")
    prepare_dataset(str(src), str(tmp_path / "o"))
    texts = {r["text"] for r in _read_jsonl(tmp_path / "o" / "train.jsonl")
             + _read_jsonl(tmp_path / "o" / "valid.jsonl")}
    assert texts == {"alpha", "beta"}


def test_prepare_unsloth_writes_json(tmp_path):
    src = tmp_path / "d.jsonl"
    src.write_text('{"text": "x"}\n')
    prepare_dataset(str(src), str(tmp_path / "o"), framework="unsloth")
    data = json.loads((tmp_path / "o" / "train.json").read_text())
    assert data == [{"text": "x"}]


def test_prepare_missing_and_empty(tmp_path):
    with pytest.raises(DatasetError):
        prepare_dataset(str(tmp_path / "nope.jsonl"), str(tmp_path / "o"))
    empty = tmp_path / "e.txt"
    empty.write_text("")
    with pytest.raises(DatasetError):
        prepare_dataset(str(empty), str(tmp_path / "o"))


def test_unsupported_format(tmp_path):
    bad = tmp_path / "d.xml"
    bad.write_text("<x/>")
    with pytest.raises(DatasetError):
        prepare_dataset(str(bad), str(tmp_path / "o"))


# ── MLX command construction ──────────────────────────────────────────────---
def test_build_mlx_command():
    cmd = build_mlx_command(
        model="mlx-community/Qwen2.5-0.5B",
        data_dir="/d",
        adapter_dir="/a",
        batch_size=2,
        iters=50,
        learning_rate=1e-4,
        num_layers=8,
        python="/usr/bin/python3",
    )
    assert cmd[:3] == ["/usr/bin/python3", "-m", "mlx_lm.lora"]
    assert "--model" in cmd and "mlx-community/Qwen2.5-0.5B" in cmd
    assert cmd[cmd.index("--data") + 1] == "/d"
    assert cmd[cmd.index("--iters") + 1] == "50"
    assert "--train" in cmd


# ── job manager ───────────────────────────────────────────────────────────---
def _mgr(tmp_path):
    cfg = Config(finetune=FinetuneConfig(jobs_dir=str(tmp_path / "jobs")))
    return FineTuneManager(cfg)


def test_create_list_get_job(tmp_path):
    src = tmp_path / "d.jsonl"
    src.write_text('{"text": "hi"}\n')
    mgr = _mgr(tmp_path)
    job = mgr.create_job("My Run", "some/model", str(src))
    assert job.status == "prepared"
    assert job.id.startswith("my-run-")
    # persisted + retrievable
    assert mgr.get_job(job.id).base_model == "some/model"
    assert [j.id for j in mgr.list_jobs()] == [job.id]
    # dataset actually prepared
    assert (tmp_path / "jobs" / job.id / "data" / "train.jsonl").is_file()


def test_start_job_launches_and_status_transitions(tmp_path, monkeypatch):
    src = tmp_path / "d.jsonl"
    src.write_text('{"text": "hi"}\n')
    mgr = _mgr(tmp_path)
    job = mgr.create_job("run", "some/model", str(src))

    # Force the mlx hardware gate and stub the subprocess with a trivial command.
    from oshell.finetune import manager as mod

    monkeypatch.setattr(mod, "detect_hardware", lambda: _FakeHW())
    monkeypatch.setattr(
        mod, "build_mlx_command", lambda **kw: ["python3", "-c", "print('done')"]
    )
    started = mgr.start_job(job)
    assert started.status == "running" and started.pid

    # Wait for the trivial process to finish, then status should resolve.
    import time

    for _ in range(50):
        if not _alive(started.pid):
            break
        time.sleep(0.1)
    refreshed = mgr.refresh_status(mgr.get_job(job.id))
    assert refreshed.status in ("completed", "failed")


class _FakeHW:
    framework = "mlx"
    platform = "mac_apple_silicon"

    @property
    def can_train(self):
        return True


def _alive(pid):
    import os

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
