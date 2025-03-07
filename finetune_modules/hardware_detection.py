"""
Hardware detection for fine-tuning.
This module provides functionality to detect hardware capabilities for fine-tuning.
"""

import platform
import subprocess
import sys
from typing import Dict

try:
    from rich.console import Console
    console = Console()
except ImportError:
    # Fallback if rich is not installed
    class FallbackConsole:
        def print(self, text, **kwargs):
            # Strip basic rich formatting
            text = text.replace("[red]", "").replace("[/red]", "")
            text = text.replace("[green]", "").replace("[/green]", "")
            text = text.replace("[yellow]", "").replace("[/yellow]", "")
            print(text)
    console = FallbackConsole()


def detect_hardware() -> Dict[str, str]:
    """
    Detect hardware capabilities for fine-tuning.
    
    Returns:
        Dictionary with hardware information and recommended framework
    """
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Default to CPU
    result = {
        "platform": "cpu",
        "framework": "cpu"
    }
    
    # Check for Apple Silicon
    if system == "darwin" and ("arm" in machine or "m1" in machine or "m2" in machine):
        result["platform"] = "mac_apple_silicon"
        result["framework"] = "mlx"
        return result
    
    # Check for Mac Intel
    if system == "darwin":
        result["platform"] = "mac_intel"
        result["framework"] = "cpu"
        return result
    
    # Check for NVIDIA GPU on Linux
    if system == "linux":
        try:
            nvidia_smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
            if nvidia_smi.returncode == 0:
                result["platform"] = "linux_nvidia"
                result["framework"] = "unsloth"
                return result
        except FileNotFoundError:
            pass
    
    # Check for NVIDIA GPU on Windows
    if system == "windows":
        try:
            nvidia_smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True, shell=True)
            if nvidia_smi.returncode == 0:
                result["platform"] = "windows_nvidia"
                result["framework"] = "unsloth_windows"
                return result
        except FileNotFoundError:
            pass
    
    # Return the default (CPU) if no other hardware is detected
    return result
