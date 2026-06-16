"""Build and launch the MLX-LM LoRA training subprocess.

Targets the modern ``mlx_lm lora`` CLI (mlx-lm >= 0.x): it reads ``train.jsonl``
/ ``valid.jsonl`` from a ``--data`` directory and writes LoRA adapters to
``--adapter-path``. Command construction is pure and unit-tested; ``launch``
is the only side-effecting part.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def build_mlx_command(
    *,
    model: str,
    data_dir: str,
    adapter_dir: str,
    batch_size: int = 1,
    iters: int = 200,
    learning_rate: float = 1e-5,
    num_layers: int = 16,
    python: str | None = None,
) -> list[str]:
    """Return the argv for an ``mlx_lm lora`` training run."""
    return [
        python or sys.executable,
        "-m",
        "mlx_lm.lora",  # the training entrypoint (verified against mlx-lm 0.21.x)
        "--model",
        model,
        "--train",
        "--data",
        data_dir,
        "--adapter-path",
        adapter_dir,
        "--batch-size",
        str(batch_size),
        "--iters",
        str(iters),
        "--learning-rate",
        str(learning_rate),
        "--num-layers",
        str(num_layers),
    ]


def launch(cmd: list[str], log_file: str) -> int:
    """Start training detached, streaming output to ``log_file``; return the PID."""
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    log = open(log_file, "w", encoding="utf-8")  # noqa: SIM115 - handed to the child
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, text=True)
    return proc.pid
