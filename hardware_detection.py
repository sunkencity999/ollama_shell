"""
Hardware detection module for fine-tuning capabilities.
This module detects the hardware platform and returns appropriate configuration
for fine-tuning models.
"""

import platform
import subprocess
from typing import Dict, Any


def detect_hardware() -> Dict[str, Any]:
    """
    Detect the hardware platform and return appropriate configuration.
    
    Returns:
        Dict with platform, framework, and requirements information
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        # Check if it's Apple Silicon
        processor = platform.processor()
        if processor == "arm" or "Apple" in platform.processor():  # Apple Silicon (M1/M2/M3)
            return {
                "platform": "mac_apple_silicon",
                "framework": "mlx",
                "requirements": ["mlx", "mlx-lm", "transformers", "datasets", 
                                "huggingface_hub"]
            }
        else:  # Intel Mac
            return {
                "platform": "mac_intel",
                "framework": "cpu_only",
                "requirements": ["transformers", "datasets", "accelerate", "peft", "trl"]
            }
    
    elif system == "Linux":
        # Check for NVIDIA GPU
        try:
            nvidia_smi = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE, timeout=5)
            if nvidia_smi.returncode == 0:
                # NVIDIA GPU available
                return {
                    "platform": "linux_nvidia",
                    "framework": "unsloth",
                    "requirements": ["unsloth", "transformers", "datasets", 
                                    "trl", "accelerate", "peft"]
                }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # No NVIDIA GPU or nvidia-smi not found
        return {
            "platform": "linux_cpu",
            "framework": "cpu_only",
            "requirements": ["transformers", "datasets", "accelerate", "peft", "trl"]
        }
    
    elif system == "Windows":
        # Check for NVIDIA GPU
        try:
            nvidia_smi = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE, timeout=5)
            if nvidia_smi.returncode == 0:
                # NVIDIA GPU available
                return {
                    "platform": "windows_nvidia",
                    "framework": "unsloth_windows",
                    "requirements": ["unsloth[windows]", "transformers", "datasets", 
                                    "trl", "accelerate", "peft"]
                }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # No NVIDIA GPU or nvidia-smi not found
        return {
            "platform": "windows_cpu",
            "framework": "cpu_only",
            "requirements": ["transformers", "datasets", "accelerate", "peft", "trl"]
        }
    
    # Default fallback
    return {
        "platform": "unknown",
        "framework": "cpu_only",
        "requirements": ["transformers", "datasets", "accelerate", "peft", "trl"]
    }


if __name__ == "__main__":
    # Test the hardware detection
    config = detect_hardware()
    print(f"Platform: {config['platform']}")
    print(f"Framework: {config['framework']}")
    print(f"Requirements: {', '.join(config['requirements'])}")
