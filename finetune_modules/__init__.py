"""
Fine-tuning modules for Ollama Shell.

This package contains modules for fine-tuning Ollama models using different frameworks.
"""

from .manager import FineTuningManager
from .hardware_detection import detect_hardware
from .venv_utils import ensure_venv_exists, get_venv_path, get_venv_python_cmd

__all__ = [
    "FineTuningManager",
    "detect_hardware",
    "ensure_venv_exists",
    "get_venv_path",
    "get_venv_python_cmd"
]
