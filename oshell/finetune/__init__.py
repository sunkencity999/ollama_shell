"""Local LoRA fine-tuning — clean successor to ``finetune.py`` + ``finetune_modules/``.

Scope, by design, is the part that can live in a tidy, tested core:

* ``hardware``  — detect platform → framework (mlx / unsloth / cpu)
* ``datasets``  — normalize jsonl/json/csv/txt into a training dir
* ``manager``   — create/list/inspect jobs (metadata persisted as JSON)
* ``mlx_runner``— build & launch the ``mlx_lm lora`` subprocess; read status

The actual training *execution* is a subprocess to ``mlx_lm`` (Apple Silicon)
or ``unsloth`` (NVIDIA); everything up to and including command construction is
unit-tested, so the only unverifiable-in-CI step is the GPU/MLX run itself.
"""

from __future__ import annotations

from .datasets import DatasetError, prepare_dataset
from .hardware import HardwareInfo, detect_hardware
from .manager import FineTuneManager, Job

__all__ = [
    "HardwareInfo",
    "detect_hardware",
    "prepare_dataset",
    "DatasetError",
    "FineTuneManager",
    "Job",
]
