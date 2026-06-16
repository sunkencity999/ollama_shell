"""Detect the local training backend.

Apple Silicon → MLX; NVIDIA (Linux/Windows) → Unsloth; everything else → CPU
(unsupported for practical LoRA training, but reported honestly).
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class HardwareInfo:
    platform: str  # mac_apple_silicon | mac_intel | linux_nvidia | windows_nvidia | cpu
    framework: str  # mlx | unsloth | cpu

    @property
    def can_train(self) -> bool:
        return self.framework in ("mlx", "unsloth")


def _has_nvidia() -> bool:
    if shutil.which("nvidia-smi") is None:
        return False
    try:
        return subprocess.run(["nvidia-smi"], capture_output=True).returncode == 0
    except OSError:  # pragma: no cover - defensive
        return False


def detect_hardware() -> HardwareInfo:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        if machine in ("arm64", "aarch64") or "arm" in machine:
            return HardwareInfo("mac_apple_silicon", "mlx")
        return HardwareInfo("mac_intel", "cpu")

    if system in ("linux", "windows") and _has_nvidia():
        return HardwareInfo(f"{system}_nvidia", "unsloth")

    return HardwareInfo("cpu", "cpu")
