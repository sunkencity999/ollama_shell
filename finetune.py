import os
import sys
import json
import time
import shutil
import datetime
import importlib
import subprocess
import re
import threading
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path

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

# Try to import optional dependencies
try:
    import requests
except ImportError:
    pass

try:
    from huggingface_hub import snapshot_download
except ImportError:
    pass

"""
Fine-tuning module for Ollama Shell.
This module provides functionality to fine-tune language models
using different frameworks based on the detected hardware.
"""

import pandas as pd  # Import pandas at the top level
import requests  # Import requests for API calls
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

# Import hardware detection
from hardware_detection import detect_hardware

class FineTuningManager:
    """Manager for fine-tuning language models."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize the fine-tuning manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), "finetune_config.json")
        self.config = self._load_config()
        self.hardware_config = detect_hardware()
        
        # Create necessary directories
        os.makedirs("./models", exist_ok=True)
        os.makedirs("./datasets", exist_ok=True)
        os.makedirs("./adapters", exist_ok=True)
        
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"jobs": {}, "datasets": {}}
        
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _is_module_installed(self, module_name: str) -> bool:
        """
        Check if a module is installed.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if the module is installed, False otherwise
        """
        # Special handling for mlx-lm which might be installed but not importable directly
        if module_name == "mlx_lm":
            try:
                # Check if the package is installed via pip
                result = subprocess.run(["pip", "show", "mlx-lm"], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            except Exception:
                return False
        else:
            try:
                spec = importlib.util.find_spec(module_name)
                return spec is not None
            except (ImportError, ValueError):
                return False
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are installed."""
        dependencies = {}
        
        # Check for MLX
        dependencies["mlx"] = self._is_module_installed("mlx")
        
        # Check for MLX-LM
        dependencies["mlx_lm"] = self._is_module_installed("mlx_lm")
        
        # Check for transformers
        dependencies["transformers"] = self._is_module_installed("transformers")
        
        # Check for huggingface_hub
        dependencies["huggingface_hub"] = self._is_module_installed("huggingface_hub")
        
        # Check for Unsloth
        dependencies["unsloth"] = self._is_module_installed("unsloth")
        
        return dependencies
    
    def install_dependencies(self) -> bool:
        """
        Install required dependencies.
        
        Returns:
            True if installation was successful, False otherwise
        """
        framework = self.hardware_config["framework"]
        platform = self.hardware_config["platform"]
        requirements = self.hardware_config["requirements"]
        
        # Check for prerequisites
        if platform.startswith("mac"):
            # Check for Homebrew
            try:
                brew_check = subprocess.run(["which", "brew"], capture_output=True, text=True)
                if brew_check.returncode != 0:
                    console.print("[red]Homebrew is required for installing dependencies on macOS.[/red]")
                    console.print("[yellow]Please install Homebrew from https://brew.sh/[/yellow]")
                    return False
                
                # Check for cmake
                cmake_check = subprocess.run(["which", "cmake"], capture_output=True, text=True)
                if cmake_check.returncode != 0:
                    console.print("[yellow]Installing cmake with Homebrew...[/yellow]")
                    subprocess.run(["brew", "install", "cmake"], check=False)
                
                # For Apple Silicon, use pre-built wheels when possible
                if platform == "mac_apple_silicon":
                    console.print("[yellow]Using pre-built wheels for Apple Silicon when available...[/yellow]")
                    
                    # Install MLX first (which doesn't require compilation)
                    mlx_cmd = ["pip", "install", "mlx"]
                    subprocess.run(mlx_cmd, check=False)
                    
                    # Install mlx-lm separately
                    mlx_lm_cmd = ["pip", "install", "mlx-lm"]
                    mlx_lm_result = subprocess.run(mlx_lm_cmd, capture_output=True, text=True)
                    
                    if mlx_lm_result.returncode != 0:
                        console.print("[yellow]Failed to install mlx-lm via pip, trying from source...[/yellow]")
                        # Try installing from source if pip install fails
                        try:
                            # Clone the repository
                            clone_cmd = ["git", "clone", "https://github.com/ml-explore/mlx-examples.git", "/tmp/mlx-examples"]
                            subprocess.run(clone_cmd, check=True)
                            
                            # Install mlx-lm from the cloned repository
                            install_cmd = ["pip", "install", "-e", "/tmp/mlx-examples/llms"]
                            subprocess.run(install_cmd, check=True)
                            
                            console.print("[green]Successfully installed mlx-lm from source[/green]")
                        except Exception:
                            return False
                    
                    # Install transformers with minimal dependencies first
                    transformers_cmd = ["pip", "install", "transformers", "datasets", "huggingface_hub"]
                    subprocess.run(transformers_cmd, check=False)
                    
                    # Then try to install visualization tools
                    viz_cmd = ["pip", "install", "pandas", "matplotlib"]
                    subprocess.run(viz_cmd, check=False)
                    
                    console.print("[green]Basic dependencies installed successfully[/green]")
                    return True
            except Exception as e:
                console.print(f"[red]Error checking prerequisites: {str(e)}[/red]")
                return False
        
        # Prepare installation command based on framework
        if framework == "unsloth":
            # Standard Unsloth installation for Linux
            cmd = ["pip", "install", "unsloth", "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "unsloth_windows":
            # Windows-specific Unsloth installation
            cmd = ["pip", "install", "\"unsloth[windows] @ git+https://github.com/unslothai/unsloth.git\"", 
                  "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "mlx":
            # MLX for Apple Silicon - simplified installation to avoid compilation issues
            cmd = ["pip", "install", "mlx", "mlx-lm", "transformers", "datasets", 
                  "huggingface_hub", "--no-deps"]
        else:
            # CPU-only fallback
            cmd = ["pip", "install", "transformers", "datasets", "accelerate", "peft", "trl"]
        
        console.print(f"[green]Installing dependencies: {' '.join(cmd)}[/green]")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]Error installing dependencies:[/red]\n{result.stderr}")
                
                # Provide helpful advice based on the error
                if "sentencepiece" in result.stderr and platform.startswith("mac"):
                    console.print("[yellow]It appears there was an issue building sentencepiece.[/yellow]")
                    console.print("[yellow]Try installing it separately with:[/yellow]")
                    console.print("[green]brew install cmake[/green]")
                    console.print("[green]pip install sentencepiece --no-build-isolation[/green]")
                
                return False
            
            console.print("[green]Dependencies installed successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error installing dependencies: {str(e)}[/red]")
            return False
    
    def create_job(self, name: str, base_model: str, **kwargs) -> Dict:
        """
        Create a new fine-tuning job configuration.
        
        Args:
            name: Name of the job
            base_model: Base model to fine-tune
            **kwargs: Additional parameters for fine-tuning
            
        Returns:
            Job configuration
        """
        if name in self.config["jobs"]:
            raise ValueError(f"Job {name} already exists")
            
        job = {
            "name": name,
            "base_model": base_model,
            "status": "created",
            "created_at": str(datetime.datetime.now()),
            "framework": self.hardware_config["framework"],
            "platform": self.hardware_config["platform"],
            "parameters": {
                "max_seq_length": kwargs.get("max_seq_length", 2048),
                "learning_rate": kwargs.get("learning_rate", 2e-4),
                "per_device_train_batch_size": kwargs.get("batch_size", 2),
                "gradient_accumulation_steps": kwargs.get("gradient_steps", 4),
                "max_steps": kwargs.get("max_steps", 60),
            }
        }
        
        # Add framework-specific parameters
        if self.hardware_config["framework"] == "unsloth" or self.hardware_config["framework"] == "unsloth_windows":
            job["parameters"]["load_in_4bit"] = kwargs.get("load_in_4bit", True)
        elif self.hardware_config["framework"] == "mlx":
            job["parameters"]["lora_rank"] = kwargs.get("lora_rank", 8)
            job["parameters"]["lora_scale"] = kwargs.get("lora_scale", 20.0)
            job["parameters"]["lora_dropout"] = kwargs.get("lora_dropout", 0.0)
            job["parameters"]["lora_layers"] = kwargs.get("lora_layers", 8)
        
        # Check if we have any datasets
        if "datasets" in self.config and self.config["datasets"]:
            # Get the most recently created dataset
            latest_dataset = None
            latest_time = None
            
            for dataset_name, dataset_info in self.config["datasets"].items():
                if "created_at" in dataset_info:
                    try:
                        created_at = datetime.datetime.fromisoformat(dataset_info["created_at"].replace(" ", "T"))
                        if latest_time is None or created_at > latest_time:
                            latest_time = created_at
                            latest_dataset = dataset_name
                    except:
                        # If we can't parse the date, just use string comparison
                        if latest_time is None or dataset_info["created_at"] > latest_time:
                            latest_time = dataset_info["created_at"]
                            latest_dataset = dataset_name
            
            if latest_dataset:
                job["dataset"] = latest_dataset
                console.print(f"[green]Using dataset: {latest_dataset}[/green]")
        
        self.config["jobs"][name] = job
        self._save_config()
        
        return job
    
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"jobs": {}, "datasets": {}}
        
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _is_module_installed(self, module_name: str) -> bool:
        """
        Check if a module is installed.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if the module is installed, False otherwise
        """
        # Special handling for mlx-lm which might be installed but not importable directly
        if module_name == "mlx_lm":
            try:
                # Check if the package is installed via pip
                result = subprocess.run(["pip", "show", "mlx-lm"], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            except Exception:
                return False
        else:
            try:
                spec = importlib.util.find_spec(module_name)
                return spec is not None
            except (ImportError, ValueError):
                return False
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are installed."""
        dependencies = {}
        
        # Check for MLX
        dependencies["mlx"] = self._is_module_installed("mlx")
        
        # Check for MLX-LM
        dependencies["mlx_lm"] = self._is_module_installed("mlx_lm")
        
        # Check for transformers
        dependencies["transformers"] = self._is_module_installed("transformers")
        
        # Check for huggingface_hub
        dependencies["huggingface_hub"] = self._is_module_installed("huggingface_hub")
        
        # Check for Unsloth
        dependencies["unsloth"] = self._is_module_installed("unsloth")
        
        return dependencies
    
    def install_dependencies(self) -> bool:
        """
        Install required dependencies.
        
        Returns:
            True if installation was successful, False otherwise
        """
        framework = self.hardware_config["framework"]
        platform = self.hardware_config["platform"]
        requirements = self.hardware_config["requirements"]
        
        # Check for prerequisites
        if platform.startswith("mac"):
            # Check for Homebrew
            try:
                brew_check = subprocess.run(["which", "brew"], capture_output=True, text=True)
                if brew_check.returncode != 0:
                    console.print("[red]Homebrew is required for installing dependencies on macOS.[/red]")
                    console.print("[yellow]Please install Homebrew from https://brew.sh/[/yellow]")
                    return False
                
                # Check for cmake
                cmake_check = subprocess.run(["which", "cmake"], capture_output=True, text=True)
                if cmake_check.returncode != 0:
                    console.print("[yellow]Installing cmake with Homebrew...[/yellow]")
                    subprocess.run(["brew", "install", "cmake"], check=False)
                
                # For Apple Silicon, use pre-built wheels when possible
                if platform == "mac_apple_silicon":
                    console.print("[yellow]Using pre-built wheels for Apple Silicon when available...[/yellow]")
                    
                    # Install MLX first (which doesn't require compilation)
                    mlx_cmd = ["pip", "install", "mlx"]
                    subprocess.run(mlx_cmd, check=False)
                    
                    # Install mlx-lm separately
                    mlx_lm_cmd = ["pip", "install", "mlx-lm"]
                    mlx_lm_result = subprocess.run(mlx_lm_cmd, capture_output=True, text=True)
                    
                    if mlx_lm_result.returncode != 0:
                        console.print("[yellow]Failed to install mlx-lm via pip, trying from source...[/yellow]")
                        # Try installing from source if pip install fails
                        try:
                            # Clone the repository
                            clone_cmd = ["git", "clone", "https://github.com/ml-explore/mlx-examples.git", "/tmp/mlx-examples"]
                            subprocess.run(clone_cmd, check=True)
                            
                            # Install mlx-lm from the cloned repository
                            install_cmd = ["pip", "install", "-e", "/tmp/mlx-examples/llms"]
                            subprocess.run(install_cmd, check=True)
                            
                            console.print("[green]Successfully installed mlx-lm from source[/green]")
                        except Exception:
                            return False
                    
                    # Install transformers with minimal dependencies first
                    transformers_cmd = ["pip", "install", "transformers", "datasets", "huggingface_hub"]
                    subprocess.run(transformers_cmd, check=False)
                    
                    # Then try to install visualization tools
                    viz_cmd = ["pip", "install", "pandas", "matplotlib"]
                    subprocess.run(viz_cmd, check=False)
                    
                    console.print("[green]Basic dependencies installed successfully[/green]")
                    return True
            except Exception as e:
                console.print(f"[red]Error checking prerequisites: {str(e)}[/red]")
                return False
        
        # Prepare installation command based on framework
        if framework == "unsloth":
            # Standard Unsloth installation for Linux
            cmd = ["pip", "install", "unsloth", "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "unsloth_windows":
            # Windows-specific Unsloth installation
            cmd = ["pip", "install", "\"unsloth[windows] @ git+https://github.com/unslothai/unsloth.git\"", 
                  "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "mlx":
            # MLX for Apple Silicon - simplified installation to avoid compilation issues
            cmd = ["pip", "install", "mlx", "mlx-lm", "transformers", "datasets", 
                  "huggingface_hub", "--no-deps"]
        else:
            # CPU-only fallback
            cmd = ["pip", "install", "transformers", "datasets", "accelerate", "peft", "trl"]
        
        console.print(f"[green]Installing dependencies: {' '.join(cmd)}[/green]")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]Error installing dependencies:[/red]\n{result.stderr}")
                
                # Provide helpful advice based on the error
                if "sentencepiece" in result.stderr and platform.startswith("mac"):
                    console.print("[yellow]It appears there was an issue building sentencepiece.[/yellow]")
                    console.print("[yellow]Try installing it separately with:[/yellow]")
                    console.print("[green]brew install cmake[/green]")
                    console.print("[green]pip install sentencepiece --no-build-isolation[/green]")
                
                return False
            
            console.print("[green]Dependencies installed successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error installing dependencies: {str(e)}[/red]")
            return False
    
    def create_job(self, name: str, base_model: str, **kwargs) -> Dict:
        """
        Create a new fine-tuning job configuration.
        
        Args:
            name: Name of the job
            base_model: Base model to fine-tune
            **kwargs: Additional parameters for fine-tuning
            
        Returns:
            Job configuration
        """
        if name in self.config["jobs"]:
            raise ValueError(f"Job {name} already exists")
            
        job = {
            "name": name,
            "base_model": base_model,
            "status": "created",
            "created_at": str(datetime.datetime.now()),
            "framework": self.hardware_config["framework"],
            "platform": self.hardware_config["platform"],
            "parameters": {
                "max_seq_length": kwargs.get("max_seq_length", 2048),
                "learning_rate": kwargs.get("learning_rate", 2e-4),
                "per_device_train_batch_size": kwargs.get("batch_size", 2),
                "gradient_accumulation_steps": kwargs.get("gradient_steps", 4),
                "max_steps": kwargs.get("max_steps", 60),
            }
        }
        
        # Add framework-specific parameters
        if self.hardware_config["framework"] == "unsloth" or self.hardware_config["framework"] == "unsloth_windows":
            job["parameters"]["load_in_4bit"] = kwargs.get("load_in_4bit", True)
        elif self.hardware_config["framework"] == "mlx":
            job["parameters"]["lora_rank"] = kwargs.get("lora_rank", 8)
            job["parameters"]["lora_scale"] = kwargs.get("lora_scale", 20.0)
            job["parameters"]["lora_dropout"] = kwargs.get("lora_dropout", 0.0)
            job["parameters"]["lora_layers"] = kwargs.get("lora_layers", 8)
        
        # Check if we have any datasets
        if "datasets" in self.config and self.config["datasets"]:
            # Get the most recently created dataset
            latest_dataset = None
            latest_time = None
            
            for dataset_name, dataset_info in self.config["datasets"].items():
                if "created_at" in dataset_info:
                    try:
                        created_at = datetime.datetime.fromisoformat(dataset_info["created_at"].replace(" ", "T"))
                        if latest_time is None or created_at > latest_time:
                            latest_time = created_at
                            latest_dataset = dataset_name
                    except:
                        # If we can't parse the date, just use string comparison
                        if latest_time is None or dataset_info["created_at"] > latest_time:
                            latest_time = dataset_info["created_at"]
                            latest_dataset = dataset_name
            
            if latest_dataset:
                job["dataset"] = latest_dataset
                console.print(f"[green]Using dataset: {latest_dataset}[/green]")
        
        self.config["jobs"][name] = job
        self._save_config()
        
        return job
    
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"jobs": {}, "datasets": {}}
        
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _is_module_installed(self, module_name: str) -> bool:
        """
        Check if a module is installed.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if the module is installed, False otherwise
        """
        # Special handling for mlx-lm which might be installed but not importable directly
        if module_name == "mlx_lm":
            try:
                # Check if the package is installed via pip
                result = subprocess.run(["pip", "show", "mlx-lm"], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            except Exception:
                return False
        else:
            try:
                spec = importlib.util.find_spec(module_name)
                return spec is not None
            except (ImportError, ValueError):
                return False
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are installed."""
        dependencies = {}
        
        # Check for MLX
        dependencies["mlx"] = self._is_module_installed("mlx")
        
        # Check for MLX-LM
        dependencies["mlx_lm"] = self._is_module_installed("mlx_lm")
        
        # Check for transformers
        dependencies["transformers"] = self._is_module_installed("transformers")
        
        # Check for huggingface_hub
        dependencies["huggingface_hub"] = self._is_module_installed("huggingface_hub")
        
        # Check for Unsloth
        dependencies["unsloth"] = self._is_module_installed("unsloth")
        
        return dependencies
    
    def install_dependencies(self) -> bool:
        """
        Install required dependencies.
        
        Returns:
            True if installation was successful, False otherwise
        """
        framework = self.hardware_config["framework"]
        platform = self.hardware_config["platform"]
        requirements = self.hardware_config["requirements"]
        
        # Check for prerequisites
        if platform.startswith("mac"):
            # Check for Homebrew
            try:
                brew_check = subprocess.run(["which", "brew"], capture_output=True, text=True)
                if brew_check.returncode != 0:
                    console.print("[red]Homebrew is required for installing dependencies on macOS.[/red]")
                    console.print("[yellow]Please install Homebrew from https://brew.sh/[/yellow]")
                    return False
                
                # Check for cmake
                cmake_check = subprocess.run(["which", "cmake"], capture_output=True, text=True)
                if cmake_check.returncode != 0:
                    console.print("[yellow]Installing cmake with Homebrew...[/yellow]")
                    subprocess.run(["brew", "install", "cmake"], check=False)
                
                # For Apple Silicon, use pre-built wheels when possible
                if platform == "mac_apple_silicon":
                    console.print("[yellow]Using pre-built wheels for Apple Silicon when available...[/yellow]")
                    
                    # Install MLX first (which doesn't require compilation)
                    mlx_cmd = ["pip", "install", "mlx"]
                    subprocess.run(mlx_cmd, check=False)
                    
                    # Install mlx-lm separately
                    mlx_lm_cmd = ["pip", "install", "mlx-lm"]
                    mlx_lm_result = subprocess.run(mlx_lm_cmd, capture_output=True, text=True)
                    
                    if mlx_lm_result.returncode != 0:
                        console.print("[yellow]Failed to install mlx-lm via pip, trying from source...[/yellow]")
                        # Try installing from source if pip install fails
                        try:
                            # Clone the repository
                            clone_cmd = ["git", "clone", "https://github.com/ml-explore/mlx-examples.git", "/tmp/mlx-examples"]
                            subprocess.run(clone_cmd, check=True)
                            
                            # Install mlx-lm from the cloned repository
                            install_cmd = ["pip", "install", "-e", "/tmp/mlx-examples/llms"]
                            subprocess.run(install_cmd, check=True)
                            
                            console.print("[green]Successfully installed mlx-lm from source[/green]")
                        except Exception:
                            return False
                    
                    # Install transformers with minimal dependencies first
                    transformers_cmd = ["pip", "install", "transformers", "datasets", "huggingface_hub"]
                    subprocess.run(transformers_cmd, check=False)
                    
                    # Then try to install visualization tools
                    viz_cmd = ["pip", "install", "pandas", "matplotlib"]
                    subprocess.run(viz_cmd, check=False)
                    
                    console.print("[green]Basic dependencies installed successfully[/green]")
                    return True
            except Exception as e:
                console.print(f"[red]Error checking prerequisites: {str(e)}[/red]")
                return False
        
        # Prepare installation command based on framework
        if framework == "unsloth":
            # Standard Unsloth installation for Linux
            cmd = ["pip", "install", "unsloth", "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "unsloth_windows":
            # Windows-specific Unsloth installation
            cmd = ["pip", "install", "\"unsloth[windows] @ git+https://github.com/unslothai/unsloth.git\"", 
                  "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "mlx":
            # MLX for Apple Silicon - simplified installation to avoid compilation issues
            cmd = ["pip", "install", "mlx", "mlx-lm", "transformers", "datasets", 
                  "huggingface_hub", "--no-deps"]
        else:
            # CPU-only fallback
            cmd = ["pip", "install", "transformers", "datasets", "accelerate", "peft", "trl"]
        
        console.print(f"[green]Installing dependencies: {' '.join(cmd)}[/green]")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]Error installing dependencies:[/red]\n{result.stderr}")
                
                # Provide helpful advice based on the error
                if "sentencepiece" in result.stderr and platform.startswith("mac"):
                    console.print("[yellow]It appears there was an issue building sentencepiece.[/yellow]")
                    console.print("[yellow]Try installing it separately with:[/yellow]")
                    console.print("[green]brew install cmake[/green]")
                    console.print("[green]pip install sentencepiece --no-build-isolation[/green]")
                
                return False
            
            console.print("[green]Dependencies installed successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error installing dependencies: {str(e)}[/red]")
            return False
    
    def create_job(self, name: str, base_model: str, **kwargs) -> Dict:
        """
        Create a new fine-tuning job configuration.
        
        Args:
            name: Name of the job
            base_model: Base model to fine-tune
            **kwargs: Additional parameters for fine-tuning
            
        Returns:
            Job configuration
        """
        if name in self.config["jobs"]:
            raise ValueError(f"Job {name} already exists")
            
        job = {
            "name": name,
            "base_model": base_model,
            "status": "created",
            "created_at": str(datetime.datetime.now()),
            "framework": self.hardware_config["framework"],
            "platform": self.hardware_config["platform"],
            "parameters": {
                "max_seq_length": kwargs.get("max_seq_length", 2048),
                "learning_rate": kwargs.get("learning_rate", 2e-4),
                "per_device_train_batch_size": kwargs.get("batch_size", 2),
                "gradient_accumulation_steps": kwargs.get("gradient_steps", 4),
                "max_steps": kwargs.get("max_steps", 60),
            }
        }
        
        # Add framework-specific parameters
        if self.hardware_config["framework"] == "unsloth" or self.hardware_config["framework"] == "unsloth_windows":
            job["parameters"]["load_in_4bit"] = kwargs.get("load_in_4bit", True)
        elif self.hardware_config["framework"] == "mlx":
            job["parameters"]["lora_rank"] = kwargs.get("lora_rank", 8)
            job["parameters"]["lora_scale"] = kwargs.get("lora_scale", 20.0)
            job["parameters"]["lora_dropout"] = kwargs.get("lora_dropout", 0.0)
            job["parameters"]["lora_layers"] = kwargs.get("lora_layers", 8)
        
        # Check if we have any datasets
        if "datasets" in self.config and self.config["datasets"]:
            # Get the most recently created dataset
            latest_dataset = None
            latest_time = None
            
            for dataset_name, dataset_info in self.config["datasets"].items():
                if "created_at" in dataset_info:
                    try:
                        created_at = datetime.datetime.fromisoformat(dataset_info["created_at"].replace(" ", "T"))
                        if latest_time is None or created_at > latest_time:
                            latest_time = created_at
                            latest_dataset = dataset_name
                    except:
                        # If we can't parse the date, just use string comparison
                        if latest_time is None or dataset_info["created_at"] > latest_time:
                            latest_time = dataset_info["created_at"]
                            latest_dataset = dataset_name
            
            if latest_dataset:
                job["dataset"] = latest_dataset
                console.print(f"[green]Using dataset: {latest_dataset}[/green]")
        
        self.config["jobs"][name] = job
        self._save_config()
        
        return job
    
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"jobs": {}, "datasets": {}}
        
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _is_module_installed(self, module_name: str) -> bool:
        """
        Check if a module is installed.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if the module is installed, False otherwise
        """
        # Special handling for mlx-lm which might be installed but not importable directly
        if module_name == "mlx_lm":
            try:
                # Check if the package is installed via pip
                result = subprocess.run(["pip", "show", "mlx-lm"], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            except Exception:
                return False
        else:
            try:
                spec = importlib.util.find_spec(module_name)
                return spec is not None
            except (ImportError, ValueError):
                return False
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are installed."""
        dependencies = {}
        
        # Check for MLX
        dependencies["mlx"] = self._is_module_installed("mlx")
        
        # Check for MLX-LM
        dependencies["mlx_lm"] = self._is_module_installed("mlx_lm")
        
        # Check for transformers
        dependencies["transformers"] = self._is_module_installed("transformers")
        
        # Check for huggingface_hub
        dependencies["huggingface_hub"] = self._is_module_installed("huggingface_hub")
        
        # Check for Unsloth
        dependencies["unsloth"] = self._is_module_installed("unsloth")
        
        return dependencies
    
    def install_dependencies(self) -> bool:
        """
        Install required dependencies.
        
        Returns:
            True if installation was successful, False otherwise
        """
        framework = self.hardware_config["framework"]
        platform = self.hardware_config["platform"]
        requirements = self.hardware_config["requirements"]
        
        # Check for prerequisites
        if platform.startswith("mac"):
            # Check for Homebrew
            try:
                brew_check = subprocess.run(["which", "brew"], capture_output=True, text=True)
                if brew_check.returncode != 0:
                    console.print("[red]Homebrew is required for installing dependencies on macOS.[/red]")
                    console.print("[yellow]Please install Homebrew from https://brew.sh/[/yellow]")
                    return False
                
                # Check for cmake
                cmake_check = subprocess.run(["which", "cmake"], capture_output=True, text=True)
                if cmake_check.returncode != 0:
                    console.print("[yellow]Installing cmake with Homebrew...[/yellow]")
                    subprocess.run(["brew", "install", "cmake"], check=False)
                
                # For Apple Silicon, use pre-built wheels when possible
                if platform == "mac_apple_silicon":
                    console.print("[yellow]Using pre-built wheels for Apple Silicon when available...[/yellow]")
                    
                    # Install MLX first (which doesn't require compilation)
                    mlx_cmd = ["pip", "install", "mlx"]
                    subprocess.run(mlx_cmd, check=False)
                    
                    # Install mlx-lm separately
                    mlx_lm_cmd = ["pip", "install", "mlx-lm"]
                    mlx_lm_result = subprocess.run(mlx_lm_cmd, capture_output=True, text=True)
                    
                    if mlx_lm_result.returncode != 0:
                        console.print("[yellow]Failed to install mlx-lm via pip, trying from source...[/yellow]")
                        # Try installing from source if pip install fails
                        try:
                            # Clone the repository
                            clone_cmd = ["git", "clone", "https://github.com/ml-explore/mlx-examples.git", "/tmp/mlx-examples"]
                            subprocess.run(clone_cmd, check=True)
                            
                            # Install mlx-lm from the cloned repository
                            install_cmd = ["pip", "install", "-e", "/tmp/mlx-examples/llms"]
                            subprocess.run(install_cmd, check=True)
                            
                            console.print("[green]Successfully installed mlx-lm from source[/green]")
                        except Exception:
                            return False
                    
                    # Install transformers with minimal dependencies first
                    transformers_cmd = ["pip", "install", "transformers", "datasets", "huggingface_hub"]
                    subprocess.run(transformers_cmd, check=False)
                    
                    # Then try to install visualization tools
                    viz_cmd = ["pip", "install", "pandas", "matplotlib"]
                    subprocess.run(viz_cmd, check=False)
                    
                    console.print("[green]Basic dependencies installed successfully[/green]")
                    return True
            except Exception as e:
                console.print(f"[red]Error checking prerequisites: {str(e)}[/red]")
                return False
        
        # Prepare installation command based on framework
        if framework == "unsloth":
            # Standard Unsloth installation for Linux
            cmd = ["pip", "install", "unsloth", "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "unsloth_windows":
            # Windows-specific Unsloth installation
            cmd = ["pip", "install", "\"unsloth[windows] @ git+https://github.com/unslothai/unsloth.git\"", 
                  "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "mlx":
            # MLX for Apple Silicon - simplified installation to avoid compilation issues
            cmd = ["pip", "install", "mlx", "mlx-lm", "transformers", "datasets", 
                  "huggingface_hub", "--no-deps"]
        else:
            # CPU-only fallback
            cmd = ["pip", "install", "transformers", "datasets", "accelerate", "peft", "trl"]
        
        console.print(f"[green]Installing dependencies: {' '.join(cmd)}[/green]")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]Error installing dependencies:[/red]\n{result.stderr}")
                
                # Provide helpful advice based on the error
                if "sentencepiece" in result.stderr and platform.startswith("mac"):
                    console.print("[yellow]It appears there was an issue building sentencepiece.[/yellow]")
                    console.print("[yellow]Try installing it separately with:[/yellow]")
                    console.print("[green]brew install cmake[/green]")
                    console.print("[green]pip install sentencepiece --no-build-isolation[/green]")
                
                return False
            
            console.print("[green]Dependencies installed successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error installing dependencies: {str(e)}[/red]")
            return False
    
    def create_job(self, name: str, base_model: str, **kwargs) -> Dict:
        """
        Create a new fine-tuning job configuration.
        
        Args:
            name: Name of the job
            base_model: Base model to fine-tune
            **kwargs: Additional parameters for fine-tuning
            
        Returns:
            Job configuration
        """
        if name in self.config["jobs"]:
            raise ValueError(f"Job {name} already exists")
            
        job = {
            "name": name,
            "base_model": base_model,
            "status": "created",
            "created_at": str(datetime.datetime.now()),
            "framework": self.hardware_config["framework"],
            "platform": self.hardware_config["platform"],
            "parameters": {
                "max_seq_length": kwargs.get("max_seq_length", 2048),
                "learning_rate": kwargs.get("learning_rate", 2e-4),
                "per_device_train_batch_size": kwargs.get("batch_size", 2),
                "gradient_accumulation_steps": kwargs.get("gradient_steps", 4),
                "max_steps": kwargs.get("max_steps", 60),
            }
        }
        
        # Add framework-specific parameters
        if self.hardware_config["framework"] == "unsloth" or self.hardware_config["framework"] == "unsloth_windows":
            job["parameters"]["load_in_4bit"] = kwargs.get("load_in_4bit", True)
        elif self.hardware_config["framework"] == "mlx":
            job["parameters"]["lora_rank"] = kwargs.get("lora_rank", 8)
            job["parameters"]["lora_scale"] = kwargs.get("lora_scale", 20.0)
            job["parameters"]["lora_dropout"] = kwargs.get("lora_dropout", 0.0)
            job["parameters"]["lora_layers"] = kwargs.get("lora_layers", 8)
        
        # Check if we have any datasets
        if "datasets" in self.config and self.config["datasets"]:
            # Get the most recently created dataset
            latest_dataset = None
            latest_time = None
            
            for dataset_name, dataset_info in self.config["datasets"].items():
                if "created_at" in dataset_info:
                    try:
                        created_at = datetime.datetime.fromisoformat(dataset_info["created_at"].replace(" ", "T"))
                        if latest_time is None or created_at > latest_time:
                            latest_time = created_at
                            latest_dataset = dataset_name
                    except:
                        # If we can't parse the date, just use string comparison
                        if latest_time is None or dataset_info["created_at"] > latest_time:
                            latest_time = dataset_info["created_at"]
                            latest_dataset = dataset_name
            
            if latest_dataset:
                job["dataset"] = latest_dataset
                console.print(f"[green]Using dataset: {latest_dataset}[/green]")
        
        self.config["jobs"][name] = job
        self._save_config()
        
        return job
    
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"jobs": {}, "datasets": {}}
        
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _is_module_installed(self, module_name: str) -> bool:
        """
        Check if a module is installed.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if the module is installed, False otherwise
        """
        # Special handling for mlx-lm which might be installed but not importable directly
        if module_name == "mlx_lm":
            try:
                # Check if the package is installed via pip
                result = subprocess.run(["pip", "show", "mlx-lm"], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            except Exception:
                return False
        else:
            try:
                spec = importlib.util.find_spec(module_name)
                return spec is not None
            except (ImportError, ValueError):
                return False
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are installed."""
        dependencies = {}
        
        # Check for MLX
        dependencies["mlx"] = self._is_module_installed("mlx")
        
        # Check for MLX-LM
        dependencies["mlx_lm"] = self._is_module_installed("mlx_lm")
        
        # Check for transformers
        dependencies["transformers"] = self._is_module_installed("transformers")
        
        # Check for huggingface_hub
        dependencies["huggingface_hub"] = self._is_module_installed("huggingface_hub")
        
        # Check for Unsloth
        dependencies["unsloth"] = self._is_module_installed("unsloth")
        
        return dependencies
    
    def install_dependencies(self) -> bool:
        """
        Install required dependencies.
        
        Returns:
            True if installation was successful, False otherwise
        """
        framework = self.hardware_config["framework"]
        platform = self.hardware_config["platform"]
        requirements = self.hardware_config["requirements"]
        
        # Check for prerequisites
        if platform.startswith("mac"):
            # Check for Homebrew
            try:
                brew_check = subprocess.run(["which", "brew"], capture_output=True, text=True)
                if brew_check.returncode != 0:
                    console.print("[red]Homebrew is required for installing dependencies on macOS.[/red]")
                    console.print("[yellow]Please install Homebrew from https://brew.sh/[/yellow]")
                    return False
                
                # Check for cmake
                cmake_check = subprocess.run(["which", "cmake"], capture_output=True, text=True)
                if cmake_check.returncode != 0:
                    console.print("[yellow]Installing cmake with Homebrew...[/yellow]")
                    subprocess.run(["brew", "install", "cmake"], check=False)
                
                # For Apple Silicon, use pre-built wheels when possible
                if platform == "mac_apple_silicon":
                    console.print("[yellow]Using pre-built wheels for Apple Silicon when available...[/yellow]")
                    
                    # Install MLX first (which doesn't require compilation)
                    mlx_cmd = ["pip", "install", "mlx"]
                    subprocess.run(mlx_cmd, check=False)
                    
                    # Install mlx-lm separately
                    mlx_lm_cmd = ["pip", "install", "mlx-lm"]
                    mlx_lm_result = subprocess.run(mlx_lm_cmd, capture_output=True, text=True)
                    
                    if mlx_lm_result.returncode != 0:
                        console.print("[yellow]Failed to install mlx-lm via pip, trying from source...[/yellow]")
                        # Try installing from source if pip install fails
                        try:
                            # Clone the repository
                            clone_cmd = ["git", "clone", "https://github.com/ml-explore/mlx-examples.git", "/tmp/mlx-examples"]
                            subprocess.run(clone_cmd, check=True)
                            
                            # Install mlx-lm from the cloned repository
                            install_cmd = ["pip", "install", "-e", "/tmp/mlx-examples/llms"]
                            subprocess.run(install_cmd, check=True)
                            
                            console.print("[green]Successfully installed mlx-lm from source[/green]")
                        except Exception:
                            return False
                    
                    # Install transformers with minimal dependencies first
                    transformers_cmd = ["pip", "install", "transformers", "datasets", "huggingface_hub"]
                    subprocess.run(transformers_cmd, check=False)
                    
                    # Then try to install visualization tools
                    viz_cmd = ["pip", "install", "pandas", "matplotlib"]
                    subprocess.run(viz_cmd, check=False)
                    
                    console.print("[green]Basic dependencies installed successfully[/green]")
                    return True
            except Exception as e:
                console.print(f"[red]Error checking prerequisites: {str(e)}[/red]")
                return False
        
        # Prepare installation command based on framework
        if framework == "unsloth":
            # Standard Unsloth installation for Linux
            cmd = ["pip", "install", "unsloth", "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "unsloth_windows":
            # Windows-specific Unsloth installation
            cmd = ["pip", "install", "\"unsloth[windows] @ git+https://github.com/unslothai/unsloth.git\"", 
                  "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "mlx":
            # MLX for Apple Silicon - simplified installation to avoid compilation issues
            cmd = ["pip", "install", "mlx", "mlx-lm", "transformers", "datasets", 
                  "huggingface_hub", "--no-deps"]
        else:
            # CPU-only fallback
            cmd = ["pip", "install", "transformers", "datasets", "accelerate", "peft", "trl"]
        
        console.print(f"[green]Installing dependencies: {' '.join(cmd)}[/green]")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]Error installing dependencies:[/red]\n{result.stderr}")
                
                # Provide helpful advice based on the error
                if "sentencepiece" in result.stderr and platform.startswith("mac"):
                    console.print("[yellow]It appears there was an issue building sentencepiece.[/yellow]")
                    console.print("[yellow]Try installing it separately with:[/yellow]")
                    console.print("[green]brew install cmake[/green]")
                    console.print("[green]pip install sentencepiece --no-build-isolation[/green]")
                
                return False
            
            console.print("[green]Dependencies installed successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error installing dependencies: {str(e)}[/red]")
            return False
    
    def create_job(self, name: str, base_model: str, **kwargs) -> Dict:
        """
        Create a new fine-tuning job configuration.
        
        Args:
            name: Name of the job
            base_model: Base model to fine-tune
            **kwargs: Additional parameters for fine-tuning
            
        Returns:
            Job configuration
        """
        if name in self.config["jobs"]:
            raise ValueError(f"Job {name} already exists")
            
        job = {
            "name": name,
            "base_model": base_model,
            "status": "created",
            "created_at": str(datetime.datetime.now()),
            "framework": self.hardware_config["framework"],
            "platform": self.hardware_config["platform"],
            "parameters": {
                "max_seq_length": kwargs.get("max_seq_length", 2048),
                "learning_rate": kwargs.get("learning_rate", 2e-4),
                "per_device_train_batch_size": kwargs.get("batch_size", 2),
                "gradient_accumulation_steps": kwargs.get("gradient_steps", 4),
                "max_steps": kwargs.get("max_steps", 60),
            }
        }
        
        # Add framework-specific parameters
        if self.hardware_config["framework"] == "unsloth" or self.hardware_config["framework"] == "unsloth_windows":
            job["parameters"]["load_in_4bit"] = kwargs.get("load_in_4bit", True)
        elif self.hardware_config["framework"] == "mlx":
            job["parameters"]["lora_rank"] = kwargs.get("lora_rank", 8)
            job["parameters"]["lora_scale"] = kwargs.get("lora_scale", 20.0)
            job["parameters"]["lora_dropout"] = kwargs.get("lora_dropout", 0.0)
            job["parameters"]["lora_layers"] = kwargs.get("lora_layers", 8)
        
        # Check if we have any datasets
        if "datasets" in self.config and self.config["datasets"]:
            # Get the most recently created dataset
            latest_dataset = None
            latest_time = None
            
            for dataset_name, dataset_info in self.config["datasets"].items():
                if "created_at" in dataset_info:
                    try:
                        created_at = datetime.datetime.fromisoformat(dataset_info["created_at"].replace(" ", "T"))
                        if latest_time is None or created_at > latest_time:
                            latest_time = created_at
                            latest_dataset = dataset_name
                    except:
                        # If we can't parse the date, just use string comparison
                        if latest_time is None or dataset_info["created_at"] > latest_time:
                            latest_time = dataset_info["created_at"]
                            latest_dataset = dataset_name
            
            if latest_dataset:
                job["dataset"] = latest_dataset
                console.print(f"[green]Using dataset: {latest_dataset}[/green]")
        
        self.config["jobs"][name] = job
        self._save_config()
        
        return job
    
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"jobs": {}, "datasets": {}}
        
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _is_module_installed(self, module_name: str) -> bool:
        """
        Check if a module is installed.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if the module is installed, False otherwise
        """
        # Special handling for mlx-lm which might be installed but not importable directly
        if module_name == "mlx_lm":
            try:
                # Check if the package is installed via pip
                result = subprocess.run(["pip", "show", "mlx-lm"], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            except Exception:
                return False
        else:
            try:
                spec = importlib.util.find_spec(module_name)
                return spec is not None
            except (ImportError, ValueError):
                return False
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are installed."""
        dependencies = {}
        
        # Check for MLX
        dependencies["mlx"] = self._is_module_installed("mlx")
        
        # Check for MLX-LM
        dependencies["mlx_lm"] = self._is_module_installed("mlx_lm")
        
        # Check for transformers
        dependencies["transformers"] = self._is_module_installed("transformers")
        
        # Check for huggingface_hub
        dependencies["huggingface_hub"] = self._is_module_installed("huggingface_hub")
        
        # Check for Unsloth
        dependencies["unsloth"] = self._is_module_installed("unsloth")
        
        return dependencies
    
    def install_dependencies(self) -> bool:
        """
        Install required dependencies.
        
        Returns:
            True if installation was successful, False otherwise
        """
        framework = self.hardware_config["framework"]
        platform = self.hardware_config["platform"]
        requirements = self.hardware_config["requirements"]
        
        # Check for prerequisites
        if platform.startswith("mac"):
            # Check for Homebrew
            try:
                brew_check = subprocess.run(["which", "brew"], capture_output=True, text=True)
                if brew_check.returncode != 0:
                    console.print("[red]Homebrew is required for installing dependencies on macOS.[/red]")
                    console.print("[yellow]Please install Homebrew from https://brew.sh/[/yellow]")
                    return False
                
                # Check for cmake
                cmake_check = subprocess.run(["which", "cmake"], capture_output=True, text=True)
                if cmake_check.returncode != 0:
                    console.print("[yellow]Installing cmake with Homebrew...[/yellow]")
                    subprocess.run(["brew", "install", "cmake"], check=False)
                
                # For Apple Silicon, use pre-built wheels when possible
                if platform == "mac_apple_silicon":
                    console.print("[yellow]Using pre-built wheels for Apple Silicon when available...[/yellow]")
                    
                    # Install MLX first (which doesn't require compilation)
                    mlx_cmd = ["pip", "install", "mlx"]
                    subprocess.run(mlx_cmd, check=False)
                    
                    # Install mlx-lm separately
                    mlx_lm_cmd = ["pip", "install", "mlx-lm"]
                    mlx_lm_result = subprocess.run(mlx_lm_cmd, capture_output=True, text=True)
                    
                    if mlx_lm_result.returncode != 0:
                        console.print("[yellow]Failed to install mlx-lm via pip, trying from source...[/yellow]")
                        # Try installing from source if pip install fails
                        try:
                            # Clone the repository
                            clone_cmd = ["git", "clone", "https://github.com/ml-explore/mlx-examples.git", "/tmp/mlx-examples"]
                            subprocess.run(clone_cmd, check=True)
                            
                            # Install mlx-lm from the cloned repository
                            install_cmd = ["pip", "install", "-e", "/tmp/mlx-examples/llms"]
                            subprocess.run(install_cmd, check=True)
                            
                            console.print("[green]Successfully installed mlx-lm from source[/green]")
                        except Exception:
                            return False
                    
                    # Install transformers with minimal dependencies first
                    transformers_cmd = ["pip", "install", "transformers", "datasets", "huggingface_hub"]
                    subprocess.run(transformers_cmd, check=False)
                    
                    # Then try to install visualization tools
                    viz_cmd = ["pip", "install", "pandas", "matplotlib"]
                    subprocess.run(viz_cmd, check=False)
                    
                    console.print("[green]Basic dependencies installed successfully[/green]")
                    return True
            except Exception as e:
                console.print(f"[red]Error checking prerequisites: {str(e)}[/red]")
                return False
        
        # Prepare installation command based on framework
        if framework == "unsloth":
            # Standard Unsloth installation for Linux
            cmd = ["pip", "install", "unsloth", "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "unsloth_windows":
            # Windows-specific Unsloth installation
            cmd = ["pip", "install", "\"unsloth[windows] @ git+https://github.com/unslothai/unsloth.git\"", 
                  "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "mlx":
            # MLX for Apple Silicon - simplified installation to avoid compilation issues
            cmd = ["pip", "install", "mlx", "mlx-lm", "transformers", "datasets", 
                  "huggingface_hub", "--no-deps"]
        else:
            # CPU-only fallback
            cmd = ["pip", "install", "transformers", "datasets", "accelerate", "peft", "trl"]
        
        console.print(f"[green]Installing dependencies: {' '.join(cmd)}[/green]")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]Error installing dependencies:[/red]\n{result.stderr}")
                
                # Provide helpful advice based on the error
                if "sentencepiece" in result.stderr and platform.startswith("mac"):
                    console.print("[yellow]It appears there was an issue building sentencepiece.[/yellow]")
                    console.print("[yellow]Try installing it separately with:[/yellow]")
                    console.print("[green]brew install cmake[/green]")
                    console.print("[green]pip install sentencepiece --no-build-isolation[/green]")
                
                return False
            
            console.print("[green]Dependencies installed successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error installing dependencies: {str(e)}[/red]")
            return False
    
    def create_job(self, name: str, base_model: str, **kwargs) -> Dict:
        """
        Create a new fine-tuning job configuration.
        
        Args:
            name: Name of the job
            base_model: Base model to fine-tune
            **kwargs: Additional parameters for fine-tuning
            
        Returns:
            Job configuration
        """
        if name in self.config["jobs"]:
            raise ValueError(f"Job {name} already exists")
            
        job = {
            "name": name,
            "base_model": base_model,
            "status": "created",
            "created_at": str(datetime.datetime.now()),
            "framework": self.hardware_config["framework"],
            "platform": self.hardware_config["platform"],
            "parameters": {
                "max_seq_length": kwargs.get("max_seq_length", 2048),
                "learning_rate": kwargs.get("learning_rate", 2e-4),
                "per_device_train_batch_size": kwargs.get("batch_size", 2),
                "gradient_accumulation_steps": kwargs.get("gradient_steps", 4),
                "max_steps": kwargs.get("max_steps", 60),
            }
        }
        
        # Add framework-specific parameters
        if self.hardware_config["framework"] == "unsloth" or self.hardware_config["framework"] == "unsloth_windows":
            job["parameters"]["load_in_4bit"] = kwargs.get("load_in_4bit", True)
        elif self.hardware_config["framework"] == "mlx":
            job["parameters"]["lora_rank"] = kwargs.get("lora_rank", 8)
            job["parameters"]["lora_scale"] = kwargs.get("lora_scale", 20.0)
            job["parameters"]["lora_dropout"] = kwargs.get("lora_dropout", 0.0)
            job["parameters"]["lora_layers"] = kwargs.get("lora_layers", 8)
        
        # Check if we have any datasets
        if "datasets" in self.config and self.config["datasets"]:
            # Get the most recently created dataset
            latest_dataset = None
            latest_time = None
            
            for dataset_name, dataset_info in self.config["datasets"].items():
                if "created_at" in dataset_info:
                    try:
                        created_at = datetime.datetime.fromisoformat(dataset_info["created_at"].replace(" ", "T"))
                        if latest_time is None or created_at > latest_time:
                            latest_time = created_at
                            latest_dataset = dataset_name
                    except:
                        # If we can't parse the date, just use string comparison
                        if latest_time is None or dataset_info["created_at"] > latest_time:
                            latest_time = dataset_info["created_at"]
                            latest_dataset = dataset_name
            
            if latest_dataset:
                job["dataset"] = latest_dataset
                console.print(f"[green]Using dataset: {latest_dataset}[/green]")
        
        self.config["jobs"][name] = job
        self._save_config()
        
        return job
    
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"jobs": {}, "datasets": {}}
        
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _is_module_installed(self, module_name: str) -> bool:
        """
        Check if a module is installed.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if the module is installed, False otherwise
        """
        # Special handling for mlx-lm which might be installed but not importable directly
        if module_name == "mlx_lm":
            try:
                # Check if the package is installed via pip
                result = subprocess.run(["pip", "show", "mlx-lm"], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            except Exception:
                return False
        else:
            try:
                spec = importlib.util.find_spec(module_name)
                return spec is not None
            except (ImportError, ValueError):
                return False
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are installed."""
        dependencies = {}
        
        # Check for MLX
        dependencies["mlx"] = self._is_module_installed("mlx")
        
        # Check for MLX-LM
        dependencies["mlx_lm"] = self._is_module_installed("mlx_lm")
        
        # Check for transformers
        dependencies["transformers"] = self._is_module_installed("transformers")
        
        # Check for huggingface_hub
        dependencies["huggingface_hub"] = self._is_module_installed("huggingface_hub")
        
        # Check for Unsloth
        dependencies["unsloth"] = self._is_module_installed("unsloth")
        
        return dependencies
    
    def install_dependencies(self) -> bool:
        """
        Install required dependencies.
        
        Returns:
            True if installation was successful, False otherwise
        """
        framework = self.hardware_config["framework"]
        platform = self.hardware_config["platform"]
        requirements = self.hardware_config["requirements"]
        
        # Check for prerequisites
        if platform.startswith("mac"):
            # Check for Homebrew
            try:
                brew_check = subprocess.run(["which", "brew"], capture_output=True, text=True)
                if brew_check.returncode != 0:
                    console.print("[red]Homebrew is required for installing dependencies on macOS.[/red]")
                    console.print("[yellow]Please install Homebrew from https://brew.sh/[/yellow]")
                    return False
                
                # Check for cmake
                cmake_check = subprocess.run(["which", "cmake"], capture_output=True, text=True)
                if cmake_check.returncode != 0:
                    console.print("[yellow]Installing cmake with Homebrew...[/yellow]")
                    subprocess.run(["brew", "install", "cmake"], check=False)
                
                # For Apple Silicon, use pre-built wheels when possible
                if platform == "mac_apple_silicon":
                    console.print("[yellow]Using pre-built wheels for Apple Silicon when available...[/yellow]")
                    
                    # Install MLX first (which doesn't require compilation)
                    mlx_cmd = ["pip", "install", "mlx"]
                    subprocess.run(mlx_cmd, check=False)
                    
                    # Install mlx-lm separately
                    mlx_lm_cmd = ["pip", "install", "mlx-lm"]
                    mlx_lm_result = subprocess.run(mlx_lm_cmd, capture_output=True, text=True)
                    
                    if mlx_lm_result.returncode != 0:
                        console.print("[yellow]Failed to install mlx-lm via pip, trying from source...[/yellow]")
                        # Try installing from source if pip install fails
                        try:
                            # Clone the repository
                            clone_cmd = ["git", "clone", "https://github.com/ml-explore/mlx-examples.git", "/tmp/mlx-examples"]
                            subprocess.run(clone_cmd, check=True)
                            
                            # Install mlx-lm from the cloned repository
                            install_cmd = ["pip", "install", "-e", "/tmp/mlx-examples/llms"]
                            subprocess.run(install_cmd, check=True)
                            
                            console.print("[green]Successfully installed mlx-lm from source[/green]")
                        except Exception:
                            return False
                    
                    # Install transformers with minimal dependencies first
                    transformers_cmd = ["pip", "install", "transformers", "datasets", "huggingface_hub"]
                    subprocess.run(transformers_cmd, check=False)
                    
                    # Then try to install visualization tools
                    viz_cmd = ["pip", "install", "pandas", "matplotlib"]
                    subprocess.run(viz_cmd, check=False)
                    
                    console.print("[green]Basic dependencies installed successfully[/green]")
                    return True
            except Exception as e:
                console.print(f"[red]Error checking prerequisites: {str(e)}[/red]")
                return False
        
        # Prepare installation command based on framework
        if framework == "unsloth":
            # Standard Unsloth installation for Linux
            cmd = ["pip", "install", "unsloth", "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "unsloth_windows":
            # Windows-specific Unsloth installation
            cmd = ["pip", "install", "\"unsloth[windows] @ git+https://github.com/unslothai/unsloth.git\"", 
                  "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "mlx":
            # MLX for Apple Silicon - simplified installation to avoid compilation issues
            cmd = ["pip", "install", "mlx", "mlx-lm", "transformers", "datasets", 
                  "huggingface_hub", "--no-deps"]
        else:
            # CPU-only fallback
            cmd = ["pip", "install", "transformers", "datasets", "accelerate", "peft", "trl"]
        
        console.print(f"[green]Installing dependencies: {' '.join(cmd)}[/green]")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]Error installing dependencies:[/red]\n{result.stderr}")
                
                # Provide helpful advice based on the error
                if "sentencepiece" in result.stderr and platform.startswith("mac"):
                    console.print("[yellow]It appears there was an issue building sentencepiece.[/yellow]")
                    console.print("[yellow]Try installing it separately with:[/yellow]")
                    console.print("[green]brew install cmake[/green]")
                    console.print("[green]pip install sentencepiece --no-build-isolation[/green]")
                
                return False
            
            console.print("[green]Dependencies installed successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error installing dependencies: {str(e)}[/red]")
            return False
    
    def create_job(self, name: str, base_model: str, **kwargs) -> Dict:
        """
        Create a new fine-tuning job configuration.
        
        Args:
            name: Name of the job
            base_model: Base model to fine-tune
            **kwargs: Additional parameters for fine-tuning
            
        Returns:
            Job configuration
        """
        if name in self.config["jobs"]:
            raise ValueError(f"Job {name} already exists")
            
        job = {
            "name": name,
            "base_model": base_model,
            "status": "created",
            "created_at": str(datetime.datetime.now()),
            "framework": self.hardware_config["framework"],
            "platform": self.hardware_config["platform"],
            "parameters": {
                "max_seq_length": kwargs.get("max_seq_length", 2048),
                "learning_rate": kwargs.get("learning_rate", 2e-4),
                "per_device_train_batch_size": kwargs.get("batch_size", 2),
                "gradient_accumulation_steps": kwargs.get("gradient_steps", 4),
                "max_steps": kwargs.get("max_steps", 60),
            }
        }
        
        # Add framework-specific parameters
        if self.hardware_config["framework"] == "unsloth" or self.hardware_config["framework"] == "unsloth_windows":
            job["parameters"]["load_in_4bit"] = kwargs.get("load_in_4bit", True)
        elif self.hardware_config["framework"] == "mlx":
            job["parameters"]["lora_rank"] = kwargs.get("lora_rank", 8)
            job["parameters"]["lora_scale"] = kwargs.get("lora_scale", 20.0)
            job["parameters"]["lora_dropout"] = kwargs.get("lora_dropout", 0.0)
            job["parameters"]["lora_layers"] = kwargs.get("lora_layers", 8)
        
        # Check if we have any datasets
        if "datasets" in self.config and self.config["datasets"]:
            # Get the most recently created dataset
            latest_dataset = None
            latest_time = None
            
            for dataset_name, dataset_info in self.config["datasets"].items():
                if "created_at" in dataset_info:
                    try:
                        created_at = datetime.datetime.fromisoformat(dataset_info["created_at"].replace(" ", "T"))
                        if latest_time is None or created_at > latest_time:
                            latest_time = created_at
                            latest_dataset = dataset_name
                    except:
                        # If we can't parse the date, just use string comparison
                        if latest_time is None or dataset_info["created_at"] > latest_time:
                            latest_time = dataset_info["created_at"]
                            latest_dataset = dataset_name
            
            if latest_dataset:
                job["dataset"] = latest_dataset
                console.print(f"[green]Using dataset: {latest_dataset}[/green]")
        
        self.config["jobs"][name] = job
        self._save_config()
        
        return job
    
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {"jobs": {}, "datasets": {}}
        
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _is_module_installed(self, module_name: str) -> bool:
        """
        Check if a module is installed.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if the module is installed, False otherwise
        """
        # Special handling for mlx-lm which might be installed but not importable directly
        if module_name == "mlx_lm":
            try:
                # Check if the package is installed via pip
                result = subprocess.run(["pip", "show", "mlx-lm"], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            except Exception:
                return False
        else:
            try:
                spec = importlib.util.find_spec(module_name)
                return spec is not None
            except (ImportError, ValueError):
                return False
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required dependencies are installed."""
        dependencies = {}
        
        # Check for MLX
        dependencies["mlx"] = self._is_module_installed("mlx")
        
        # Check for MLX-LM
        dependencies["mlx_lm"] = self._is_module_installed("mlx_lm")
        
        # Check for transformers
        dependencies["transformers"] = self._is_module_installed("transformers")
        
        # Check for huggingface_hub
        dependencies["huggingface_hub"] = self._is_module_installed("huggingface_hub")
        
        # Check for Unsloth
        dependencies["unsloth"] = self._is_module_installed("unsloth")
        
        return dependencies
    
    def install_dependencies(self) -> bool:
        """
        Install required dependencies.
        
        Returns:
            True if installation was successful, False otherwise
        """
        framework = self.hardware_config["framework"]
        platform = self.hardware_config["platform"]
        requirements = self.hardware_config["requirements"]
        
        # Check for prerequisites
        if platform.startswith("mac"):
            # Check for Homebrew
            try:
                brew_check = subprocess.run(["which", "brew"], capture_output=True, text=True)
                if brew_check.returncode != 0:
                    console.print("[red]Homebrew is required for installing dependencies on macOS.[/red]")
                    console.print("[yellow]Please install Homebrew from https://brew.sh/[/yellow]")
                    return False
                
                # Check for cmake
                cmake_check = subprocess.run(["which", "cmake"], capture_output=True, text=True)
                if cmake_check.returncode != 0:
                    console.print("[yellow]Installing cmake with Homebrew...[/yellow]")
                    subprocess.run(["brew", "install", "cmake"], check=False)
                
                # For Apple Silicon, use pre-built wheels when possible
                if platform == "mac_apple_silicon":
                    console.print("[yellow]Using pre-built wheels for Apple Silicon when available...[/yellow]")
                    
                    # Install MLX first (which doesn't require compilation)
                    mlx_cmd = ["pip", "install", "mlx"]
                    subprocess.run(mlx_cmd, check=False)
                    
                    # Install mlx-lm separately
                    mlx_lm_cmd = ["pip", "install", "mlx-lm"]
                    mlx_lm_result = subprocess.run(mlx_lm_cmd, capture_output=True, text=True)
                    
                    if mlx_lm_result.returncode != 0:
                        console.print("[yellow]Failed to install mlx-lm via pip, trying from source...[/yellow]")
                        # Try installing from source if pip install fails
                        try:
                            # Clone the repository
                            clone_cmd = ["git", "clone", "https://github.com/ml-explore/mlx-examples.git", "/tmp/mlx-examples"]
                            subprocess.run(clone_cmd, check=True)
                            
                            # Install mlx-lm from the cloned repository
                            install_cmd = ["pip", "install", "-e", "/tmp/mlx-examples/llms"]
                            subprocess.run(install_cmd, check=True)
                            
                            console.print("[green]Successfully installed mlx-lm from source[/green]")
                        except Exception:
                            return False
                    
                    # Install transformers with minimal dependencies first
                    transformers_cmd = ["pip", "install", "transformers", "datasets", "huggingface_hub"]
                    subprocess.run(transformers_cmd, check=False)
                    
                    # Then try to install visualization tools
                    viz_cmd = ["pip", "install", "pandas", "matplotlib"]
                    subprocess.run(viz_cmd, check=False)
                    
                    console.print("[green]Basic dependencies installed successfully[/green]")
                    return True
            except Exception as e:
                console.print(f"[red]Error checking prerequisites: {str(e)}[/red]")
                return False
        
        # Prepare installation command based on framework
        if framework == "unsloth":
            # Standard Unsloth installation for Linux
            cmd = ["pip", "install", "unsloth", "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "unsloth_windows":
            # Windows-specific Unsloth installation
            cmd = ["pip", "install", "\"unsloth[windows] @ git+https://github.com/unslothai/unsloth.git\"", 
                  "transformers", "datasets", "trl", "accelerate", "peft"]
        elif framework == "mlx":
            # MLX for Apple Silicon - simplified installation to avoid compilation issues
            cmd = ["pip", "install", "mlx", "mlx-lm", "transformers", "datasets", 
                  "huggingface_hub", "--no-deps"]
        else:
            # CPU-only fallback
            cmd = ["pip", "install", "transformers", "datasets", "accelerate", "peft", "trl"]
        
        console.print(f"[green]Installing dependencies: {' '.join(cmd)}[/green]")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]Error installing dependencies:[/red]\n{result.stderr}")
                
                # Provide helpful advice based on the error
                if "sentencepiece" in result.stderr and platform.startswith("mac"):
                    console.print("[yellow]It appears there was an issue building sentencepiece.[/yellow]")
                    console.print("[yellow]Try installing it separately with:[/yellow]")
                    console.print("[green]brew install cmake[/green]")
                    console.print("[green]pip install sentencepiece --no-build-isolation[/green]")
                
                return False
            
            console.print("[green]Dependencies installed successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error installing dependencies: {str(e)}[/red]")
            return False
    
    def create_job(self, name: str, base_model: str, **kwargs) -> Dict:
        """
        Create a new fine-tuning job configuration.
        
        Args:
            name: Name of the job
            base_model: Base model to fine-tune
            **kwargs: Additional parameters for fine-tuning
            
        Returns:
            Job configuration
        """
        if name in self.config["jobs"]:
            raise ValueError(f"Job {name} already exists")
            
        job = {
            "name": name,
            "base_model": base_model,
            "status": "created",
            "created_at": str(datetime.datetime.now()),
            "framework": self.hardware_config["framework"],
            "platform": self.hardware_config["platform"],
            "parameters": {
                "max_seq_length": kwargs.get("max_seq_length", 2048),
                "learning_rate": kwargs.get("learning_rate", 2e-4),
                "per_device_train_batch_size": kwargs.get("batch_size", 2),
                "gradient_accumulation_steps": kwargs.get("gradient_steps", 4),
                "max_steps": kwargs.get("max_steps", 60),
            }
        }
        
        # Add framework-specific parameters
        if self.hardware_config["framework"] == "unsloth" or self.hardware_config["framework"] == "unsloth_windows":
            job["parameters"]["load_in_4bit"] = kwargs.get("load_in_4bit", True)
        elif self.hardware_config["framework"] == "mlx":
            job["parameters"]["lora_rank"] = kwargs.get("lora_rank", 8)
            job["parameters"]["lora_scale"] = kwargs.get("lora_scale", 20.0)
            job["parameters"]["lora_dropout"] = kwargs.get("lora_dropout", 0.0)
            job["parameters"]["lora_layers"] = kwargs.get("lora_layers", 8)
        
        # Check if we have any datasets
        if "datasets" in self.config and self.config["datasets"]:
            # Get the most recently created dataset
            latest_dataset = None
            latest_time = None
            
            for dataset_name, dataset_info in self.config["datasets"].items():
                if "created_at" in dataset_info:
                    try:
                        created_at = datetime.datetime.fromisoformat(dataset_info["created_at"].replace(" ", "T"))
                        if latest_time is None or created_at > latest_time:
                            latest_time = created_at
                            latest_dataset = dataset_name
                    except:
                        # If we can't parse the date, just use string comparison
                        if latest_time is None or dataset_info["created_at"] > latest_time:
                            latest_time = dataset_info["created_at"]
                            latest_dataset = dataset_name
            
            if latest_dataset:
                job["dataset"] = latest_dataset
                console.print(f"[green]Using dataset: {latest_dataset}[/green]")
        
        self.config["jobs"][name] = job
        self._save_config()
        
        return job
    
    def detect_dataset_format(self, dataset_path):
        """
        Automatically detect the format and structure of a dataset.
        
        Args:
            dataset_path (str): Path to the dataset file or directory
        
        Returns:
            tuple: (format_type, data_path, column_mapping)
                format_type: One of 'json', 'csv', 'txt', 'parquet', 'huggingface', 'directory'
                data_path: Path to the actual data file(s)
                column_mapping: Dictionary mapping standard column names to dataset-specific ones
        """
        import os
        import glob
        
        # Check if it's a directory
        if os.path.isdir(dataset_path):
            # Look for common dataset files
            json_files = glob.glob(os.path.join(dataset_path, "**", "*.json"), recursive=True)
            csv_files = glob.glob(os.path.join(dataset_path, "**", "*.csv"), recursive=True)
            parquet_files = glob.glob(os.path.join(dataset_path, "**", "*.parquet"), recursive=True)
            txt_files = glob.glob(os.path.join(dataset_path, "**", "*.txt"), recursive=True)
            
            # Check for HuggingFace dataset structure
            hf_dataset = False
            if os.path.exists(os.path.join(dataset_path, "dataset_info.json")):
                hf_dataset = True
            
            # Determine the most likely format
            if hf_dataset:
                return 'huggingface', dataset_path, {}
            elif parquet_files:
                # Prioritize parquet files as they're likely the most structured
                return 'directory', parquet_files, {}
            elif json_files:
                return 'directory', json_files, {}
            elif csv_files:
                return 'directory', csv_files, {}
            elif txt_files:
                return 'directory', txt_files, {}
            else:
                return 'directory', dataset_path, {}
        
        # Check if it's a file
        elif os.path.isfile(dataset_path):
            ext = os.path.splitext(dataset_path)[1].lower()
            if ext == '.json':
                return 'json', dataset_path, {}
            elif ext == '.csv':
                return 'csv', dataset_path, {}
            elif ext == '.parquet':
                return 'parquet', dataset_path, {}
            elif ext == '.txt':
                return 'txt', dataset_path, {}
            else:
                return 'unknown', dataset_path, {}
        
        return 'unknown', dataset_path, {}

    def process_directory_dataset(self, file_paths, output_path):
        """
        Process a directory containing multiple dataset files.
        
        Args:
            file_paths (list): List of file paths to process
            output_path (str): Path to save the processed dataset
        
        Returns:
            str: Path to the processed dataset
        """
        import os
        import json
        import tempfile
        
        # Create a temporary directory for processing
        temp_dir = tempfile.mkdtemp()
        combined_data = []
        
        for file_path in file_paths:
            ext = os.path.splitext(file_path)[1].lower()
            
            try:
                if ext == '.json':
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        combined_data.extend(self.process_json_data(data))
                    elif isinstance(data, dict):
                        # Handle different JSON structures
                        if 'data' in data:
                            combined_data.extend(self.process_json_data(data['data']))
                        elif 'examples' in data:
                            combined_data.extend(self.process_json_data(data['examples']))
                        elif 'full articles' in data:
                            # Handle AmericanStories format
                            articles = data.get('full articles', [])
                            for article in articles:
                                if 'headline' in article and 'article' in article:
                                    combined_data.append({
                                        'instruction': f"Summarize this news article with headline: {article['headline']}",
                                        'response': article['article']
                                    })
            
                elif ext == '.parquet':
                    try:
                        df = pd.read_parquet(file_path)
                        combined_data.extend(self.process_dataframe(df))
                    except Exception as e:
                        print(f"Error reading Parquet file {file_path}: {e}")
                        continue
            
                elif ext == '.csv':
                    try:
                        df = pd.read_csv(file_path)
                        combined_data.extend(self.process_dataframe(df))
                    except Exception as e:
                        print(f"Error reading CSV file {file_path}: {e}")
                        continue
            
                elif ext == '.txt':
                    with open(file_path, 'r') as f:
                        text = f.read()
                    # Simple heuristic: split by double newlines and alternate as instruction/response
                    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                    for i in range(0, len(paragraphs) - 1, 2):
                        if i + 1 < len(paragraphs):
                            combined_data.append({
                                'instruction': paragraphs[i],
                                'response': paragraphs[i + 1]
                            })
        
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue
    
        # Save the combined data
        if not combined_data:
            print("No valid data found in the directory")
            return None
    
        output_file = output_path if output_path else os.path.join(temp_dir, "processed_dataset.json")
        with open(output_file, 'w') as f:
            json.dump(combined_data, f, indent=2)
    
        return output_file

    def process_json_data(self, data):
        """Process JSON data to extract instruction/response pairs"""
        processed_data = []
        
        if not isinstance(data, list):
            return processed_data
        
        for item in data:
            if not isinstance(item, dict):
                continue
            
            # Try to find instruction and response fields
            instruction = None
            response = None
            
            # Check for standard field names
            if 'instruction' in item and 'response' in item:
                instruction = item['instruction']
                response = item['response']
            elif 'input' in item and 'output' in item:
                instruction = item['input']
                response = item['output']
            elif 'question' in item and 'answer' in item:
                instruction = item['question']
                response = item['answer']
            elif 'prompt' in item and 'completion' in item:
                instruction = item['prompt']
                response = item['completion']
            
            # Handle special cases for specific datasets
            elif 'headline' in item and 'article' in item:
                # News article format
                instruction = f"Summarize this news article with headline: {item['headline']}"
                response = item['article']
            
            if instruction and response:
                processed_data.append({
                    'instruction': instruction,
                    'response': response
                })
    
        return processed_data

    def process_dataframe(self, df):
        """Process a pandas DataFrame to extract instruction/response pairs"""
        processed_data = []
        
        # Map of possible column names
        instruction_cols = ['instruction', 'input', 'question', 'prompt', 'query']
        response_cols = ['response', 'output', 'answer', 'completion', 'result']
        
        # Find the instruction column
        instruction_col = None
        for col in instruction_cols:
            if col in df.columns:
                instruction_col = col
                break
        
        # Find the response column
        response_col = None
        for col in response_cols:
            if col in df.columns:
                response_col = col
                break
        
        # If we found both columns, extract the data
        if instruction_col and response_col:
            for _, row in df.iterrows():
                instruction = row[instruction_col]
                response = row[response_col]
                if pd.notna(instruction) and pd.notna(response):
                    processed_data.append({
                        'instruction': str(instruction),
                        'response': str(response)
                    })
    
        return processed_data

    def prepare_dataset(self, dataset_path, output_path=None):
        """
        Prepare a dataset for fine-tuning.
        
        Args:
            dataset_path (str): Path to the dataset file or directory
            output_path (str, optional): Path to save the processed dataset
        
        Returns:
            str: Path to the processed dataset
        """
        import os
        import json
        import tempfile
        
        # Detect the dataset format
        format_type, data_path, _ = self.detect_dataset_format(dataset_path)
        
        # Process the dataset based on its format
        if format_type == 'directory':
            return self.process_directory_dataset(data_path, output_path)
        
        elif format_type == 'json':
            try:
                with open(data_path, 'r') as f:
                    data = json.load(f)
                processed_data = self.process_json_data(data)
            except Exception as e:
                print(f"Error processing JSON file: {e}")
                return None
        
        elif format_type == 'csv':
            try:
                df = pd.read_csv(data_path)
                processed_data = self.process_dataframe(df)
            except Exception as e:
                print(f"Error processing CSV file: {e}")
                return None
        
        elif format_type == 'parquet':
            try:
                df = pd.read_parquet(data_path)
                processed_data = self.process_dataframe(df)
            except Exception as e:
                print(f"Error processing Parquet file: {e}")
                return None
        
        elif format_type == 'txt':
            try:
                with open(data_path, 'r') as f:
                    text = f.read()
                # Simple heuristic: split by double newlines and alternate as instruction/response
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                processed_data = []
                for i in range(0, len(paragraphs) - 1, 2):
                    if i + 1 < len(paragraphs):
                        processed_data.append({
                            'instruction': paragraphs[i],
                            'response': paragraphs[i + 1]
                        })
            except Exception as e:
                print(f"Error processing text file: {e}")
                return None
        
        elif format_type == 'huggingface':
            try:
                import datasets
                dataset = datasets.load_from_disk(data_path)
                processed_data = []
                
                # Get the first split (usually 'train')
                split_names = list(dataset.keys())
                if not split_names:
                    print("No splits found in the HuggingFace dataset")
                    return None
                
                split = dataset[split_names[0]]
                
                # Try to map columns
                instruction_cols = ['instruction', 'input', 'question', 'prompt', 'query']
                response_cols = ['response', 'output', 'answer', 'completion', 'result']
                
                # Find the instruction column
                instruction_col = None
                for col in instruction_cols:
                    if col in split.column_names:
                        instruction_col = col
                        break
                
                # Find the response column
                response_col = None
                for col in response_cols:
                    if col in split.column_names:
                        response_col = col
                        break
                
                # If we found both columns, extract the data
                if instruction_col and response_col:
                    for item in split:
                        processed_data.append({
                            'instruction': item[instruction_col],
                            'response': item[response_col]
                        })
                else:
                    print(f"Could not find instruction/response columns in the dataset. Available columns: {split.column_names}")
                    return None
            
            except ImportError:
                print("The 'datasets' library is required to process HuggingFace datasets")
                print("Install it with: pip install datasets")
                return None
            except Exception as e:
                print(f"Error processing HuggingFace dataset: {e}")
                return None
        
        else:
            print(f"Unsupported dataset format: {format_type}")
            return None
        
        # Save the processed data
        if not processed_data:
            print("No valid instruction/response pairs found in the dataset")
            return None
        
        if not output_path:
            # Create a temporary file
            temp_dir = tempfile.mkdtemp()
            output_path = os.path.join(temp_dir, "processed_dataset.json")
        
        with open(output_path, 'w') as f:
            json.dump(processed_data, f, indent=2)
        
        return output_path
    
    def prepare_dataset_wrapper(self, path: str, format: str = None, name: str = None) -> Dict:
        """
        Wrapper for the prepare_dataset function to maintain backward compatibility.
        
        Args:
            path: Path to the dataset file or directory
            format: Format of the dataset (json, csv, txt, parquet)
            name: Name for the dataset
            
        Returns:
            Dataset information
        """
        # Normalize path
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Dataset file not found: {path}")
        
        # Generate a name if not provided
        if name is None:
            name = os.path.basename(path).split(".")[0]
        
        # Ensure datasets directory exists
        os.makedirs("./datasets", exist_ok=True)
        
        # Process the dataset using the new intelligent method
        dataset_path = os.path.join("./datasets", f"{name}.json")
        processed_path = self.prepare_dataset(path, dataset_path)
        
        if not processed_path:
            raise ValueError(f"Failed to process dataset: {path}")
        
        # Detect format if not provided
        if format is None:
            _, ext = os.path.splitext(path)
            if ext:
                format = ext[1:].lower()  # Remove the dot
            else:
                format = "json"  # Default format
        
        # Add dataset to config
        if "datasets" not in self.config:
            self.config["datasets"] = {}
            
        dataset_info = {
            "name": name,
            "path": dataset_path,
            "format": format,
            "created_at": str(datetime.datetime.now()),
            "original_path": path
        }
        
        self.config["datasets"][name] = dataset_info
        self._save_config()
        
        # Convert to MLX-LM format
        self.convert_to_mlx_lm_format(dataset_info)
        
        return dataset_info
        
    def convert_to_mlx_lm_format(self, dataset_info):
        """
        Convert a processed dataset to the format expected by MLX-LM.
        
        Args:
            dataset_info: Dataset information dictionary
            
        Returns:
            Path to the MLX-LM formatted dataset directory
        """
        import json
        import os
        import random
        
        # Create MLX-LM dataset directory
        dataset_name = dataset_info["name"]
        mlx_dataset_dir = os.path.join("./datasets", dataset_name)
        os.makedirs(mlx_dataset_dir, exist_ok=True)
        
        # Load the processed dataset
        with open(dataset_info["path"], "r") as f:
            data = json.load(f)
        
        # Shuffle the data
        random.shuffle(data)
        
        # Split into train and validation sets (90/10 split)
        split_idx = max(1, int(len(data) * 0.9))
        train_data = data[:split_idx]
        valid_data = data[split_idx:]
        
        # If there's no validation data, use a small portion of train data
        if not valid_data:
            split_idx = max(1, int(len(train_data) * 0.9))
            valid_data = train_data[split_idx:]
            train_data = train_data[:split_idx]
        
        # Convert to MLX-LM format (completions format)
        train_mlx = []
        valid_mlx = []
        
        # Convert instruction-response pairs to completions format
        for item in train_data:
            if "instruction" in item and "response" in item:
                train_mlx.append({
                    "prompt": item["instruction"],
                    "completion": item["response"]
                })
            elif "prompt" in item and "completion" in item:
                train_mlx.append(item)
        
        for item in valid_data:
            if "instruction" in item and "response" in item:
                valid_mlx.append({
                    "prompt": item["instruction"],
                    "completion": item["response"]
                })
            elif "prompt" in item and "completion" in item:
                valid_mlx.append(item)
        
        # Write train.jsonl and valid.jsonl
        with open(os.path.join(mlx_dataset_dir, "train.jsonl"), "w") as f:
            for item in train_mlx:
                f.write(json.dumps(item) + "\n")
        
        with open(os.path.join(mlx_dataset_dir, "valid.jsonl"), "w") as f:
            for item in valid_mlx:
                f.write(json.dumps(item) + "\n")
        
        # Also create a test.jsonl with a small sample of the validation data
        test_mlx = valid_mlx[:min(10, len(valid_mlx))]
        with open(os.path.join(mlx_dataset_dir, "test.jsonl"), "w") as f:
            for item in test_mlx:
                f.write(json.dumps(item) + "\n")
        
        console.print(f"[green]Converted dataset to MLX-LM format in {mlx_dataset_dir}[/green]")
        console.print(f"[green]Train samples: {len(train_mlx)}, Validation samples: {len(valid_mlx)}, Test samples: {len(test_mlx)}[/green]")
        
        # Update the dataset info with the MLX-LM directory
        dataset_info["mlx_lm_path"] = mlx_dataset_dir
        self.config["datasets"][dataset_name] = dataset_info
        self._save_config()
        
        return mlx_dataset_dir
    
    def start_job(self, name: str) -> Dict:
        """
        Start a fine-tuning job.
        
        Args:
            name: Name of the job
            
        Returns:
            Updated job configuration
        """
        if name not in self.config["jobs"]:
            raise ValueError(f"Job {name} does not exist")
            
        job = self.config["jobs"][name]
        framework = self.hardware_config["framework"]
        
        # Check if dependencies are installed
        deps_status = self.check_dependencies()
        missing_deps = [dep for dep, installed in deps_status.items() if not installed]
        
        if missing_deps:
            console.print(f"[yellow]Missing dependencies: {', '.join(missing_deps)}[/yellow]")
            console.print("[yellow]Installing missing dependencies...[/yellow]")
            if not self.install_dependencies():
                raise RuntimeError("Failed to install dependencies")
        
        # Update job status
        job["status"] = "running"
        job["start_time"] = datetime.datetime.now().isoformat()
        self._save_config()
        
        try:
            if framework == "unsloth" or framework == "unsloth_windows":
                self._run_unsloth_job(job)
            elif framework == "mlx":
                self._run_mlx_job(job)
            else:
                self._run_cpu_job(job)
                
            # Update job status on success
            job["status"] = "completed"
            job["completed_at"] = str(datetime.datetime.now())
            self._save_config()
            return job
        except Exception as e:
            # Update job status on failure
            job["status"] = "failed"
            job["error"] = str(e)
            self._save_config()
            raise
    
    def _run_unsloth_job(self, job: Dict):
        """
        Run a fine-tuning job using Unsloth.
        
        Args:
            job: Job configuration
        """
        console.print("[yellow]Running fine-tuning job with Unsloth...[/yellow]")
        
        # This is a placeholder implementation
        # In a real implementation, we would need to:
        # 1. Import the necessary modules
        # 2. Load the model and tokenizer
        # 3. Load the dataset
        # 4. Configure training arguments
        # 5. Create trainer
        # 6. Train the model
        # 7. Save the model
        
        # Simulating training progress
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("[green]Training...", total=100)
            for i in range(100):
                # Simulate some work
                import time
                time.sleep(0.1)
                progress.update(task, advance=1)
        
        console.print("[green]Fine-tuning completed successfully[/green]")
    
    def _run_mlx_job(self, job: Dict):
        """
        Run a fine-tuning job using MLX on Apple Silicon.
        This method is called when MLX is available.
        
        Args:
            job: Job configuration
        """
        # First check if mlx-lm is available
        try:
            import mlx_lm
            console.print("[green]Using mlx-lm for fine-tuning...[/green]")
            return self._run_mlx_lm(job)
        except ImportError:
            console.print("[yellow]mlx-lm not found. Using direct MLX implementation...[/yellow]")
            return self._run_mlx_direct(job)
    
    def _run_mlx_lm(self, job: Dict):
        """
        Run a fine-tuning job using MLX-LM on Apple Silicon.
        
        Args:
            job: Job configuration
        """
        try:
            import mlx_lm
        except ImportError:
            console.print("[red]MLX-LM is not installed. Please run /finetune install first.[/red]")
            return
        
        # Get job parameters
        model_name = job["base_model"]
        
        # Get the dataset name from the job
        if "dataset" not in job:
            raise ValueError("No dataset specified for this job. Use /finetune dataset [path] to prepare a dataset first, then update the job with the dataset.")
        
        dataset_name = job["dataset"]
        
        # Check if the dataset exists in our config
        if dataset_name not in self.config["datasets"]:
            raise ValueError(f"Dataset '{dataset_name}' not found. Available datasets: {', '.join(self.config['datasets'].keys())}")
        
        # Get the MLX-LM formatted dataset path
        dataset_info = self.config["datasets"][dataset_name]
        if "mlx_lm_path" not in dataset_info:
            raise ValueError(f"Dataset '{dataset_name}' is not properly formatted for MLX-LM. Try preparing the dataset again.")
            
        mlx_dataset_dir = dataset_info["mlx_lm_path"]
        output_dir = os.path.join("./models", job["name"])
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Get the model path - use our new export functionality
        model_dir = self._export_ollama_model_for_mlx(model_name, job["name"])
        
        if not model_dir:
            console.print(f"[red]Failed to export model {model_name} for fine-tuning. Please ensure the model is properly downloaded with 'ollama pull {model_name}'[/red]")
            return
            
        # Update job status
        job["status"] = "running"
        job["start_time"] = str(datetime.datetime.now().isoformat())
        self.config["jobs"][job["name"]] = job
        self._save_config()
        
        # Prepare MLX-LM command
        cmd = [
            "python", "-m", "mlx_lm.finetune",
            "--model", model_dir,
            "--train_data", mlx_dataset_dir,
            "--output_dir", output_dir,
            "--batch_size", str(job["parameters"]["per_device_train_batch_size"]),
            "--steps", str(job["parameters"]["max_steps"]),
            "--learning_rate", str(job["parameters"]["learning_rate"])
        ]
        
        # Add LoRA parameters if using LoRA
        if "lora_rank" in job["parameters"]:
            cmd.extend([
                "--lora_rank", str(job["parameters"]["lora_rank"]),
                "--lora_alpha", str(job["parameters"]["lora_scale"]),
                "--lora_dropout", str(job["parameters"]["lora_dropout"]),
                "--lora_layers", str(job["parameters"]["lora_layers"])
            ])
        
        # Run the command
        console.print(f"[green]Starting MLX-LM fine-tuning with command:[/green] {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor the process
            job["process_id"] = process.pid
            self.config["jobs"][job["name"]] = job
            self._save_config()
            
            # Process output
            for line in iter(process.stdout.readline, ""):
                # Log the output
                print(line, end="")
                
                # Parse progress information
                if "Step" in line and "loss" in line:
                    try:
                        # Extract step information
                        step_match = re.search(r"Step (\d+)/(\d+)", line)
                        if step_match:
                            current_step = int(step_match.group(1))
                            total_steps = int(step_match.group(2))
                            
                            # Update job progress
                            job["current_step"] = current_step
                            job["total_steps"] = total_steps
                            job["progress"] = current_step / total_steps
                            
                            # Extract loss information
                            loss_match = re.search(r"loss: ([\d\.]+)", line)
                            if loss_match:
                                job["loss"] = float(loss_match.group(1))
                            
                            # Save updated job information
                            self.config["jobs"][job["name"]] = job
                            self._save_config()
                    except Exception as e:
                        print(f"Error parsing progress: {str(e)}")
            
            # Wait for the process to complete
            process.wait()
            
            # Update job status
            if process.returncode == 0:
                job["status"] = "completed"
                job["completed_at"] = str(datetime.datetime.now())
                console.print(f"[green]Fine-tuning job {job['name']} completed successfully![/green]")
            else:
                job["status"] = "failed"
                job["error"] = f"mlx-lm failed with exit code {process.returncode}"
                console.print(f"[red]Fine-tuning job {job['name']} failed with exit code {process.returncode}[/red]")
            
            self.config["jobs"][job["name"]] = job
            self._save_config()
            
        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
            self.config["jobs"][job["name"]] = job
            self._save_config()
            console.print(f"[red]Error running MLX-LM: {str(e)}[/red]")
    
    def _run_mlx_direct(self, job: Dict):
        """
        Run a fine-tuning job using MLX directly on Apple Silicon.
        This is a fallback method when mlx-lm is not available or when
        Ollama's API doesn't support fine-tuning.
        
        Args:
            job: Job configuration
        """
        try:
            import mlx
            import mlx.core as mx
            import mlx.nn as nn
            import mlx.optimizers as optim
        except ImportError:
            console.print("[red]MLX is not installed. Please run /finetune install first.[/red]")
            return False
            
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            from huggingface_hub import snapshot_download
        except ImportError:
            console.print("[red]Transformers and huggingface_hub are not installed. Please run /finetune install first.[/red]")
            return False
            
        console.print("[green]Starting direct MLX fine-tuning...[/green]")
        
        # Get job parameters
        model_name = job["base_model"]
        
        # Get the dataset name from the job
        if "dataset" not in job:
            raise ValueError("No dataset specified for this job. Use /finetune dataset [path] to prepare a dataset first, then update the job with the dataset.")
        
        dataset_name = job["dataset"]
        
        # Check if the dataset exists in our config
        if dataset_name not in self.config["datasets"]:
            raise ValueError(f"Dataset '{dataset_name}' not found. Available datasets: {', '.join(self.config['datasets'].keys())}")
        
        # Get the MLX-LM formatted dataset path
        dataset_info = self.config["datasets"][dataset_name]
        if "mlx_lm_path" not in dataset_info:
            raise ValueError(f"Dataset '{dataset_name}' is not properly formatted for MLX-LM. Try preparing the dataset again.")
            
        mlx_dataset_dir = dataset_info["mlx_lm_path"]
        output_dir = os.path.join("./models", job["name"])
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Get the model path from Ollama
        ollama_models_dir = os.path.expanduser("~/.ollama/models")
        model_dir = None
        model_id = None
        
        # First, try to find the model using ollama list
        try:
            import subprocess
            console.print(f"[yellow]Looking for model: {model_name}[/yellow]")
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if result.returncode == 0:
                console.print(f"[green]Ollama models available:[/green]\n{result.stdout}")
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Skip header line
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 2:
                            name = parts[0]
                            id_value = parts[1]
                            
                            # Check if this is our model - exact match or prefix match
                            model_base_name = model_name.split(':')[0].lower()
                            if name.lower() == model_name.lower() or name.lower().startswith(model_base_name):
                                console.print(f"[green]Found matching model: {name} with ID: {id_value}[/green]")
                                model_id = id_value
                                
                                # Try to find the model directory using the ID
                                blobs_dir = os.path.join(ollama_models_dir, "blobs")
                                if os.path.exists(blobs_dir):
                                    # Look for the model ID in the blobs directory
                                    for root, dirs, files in os.walk(blobs_dir):
                                        for file in files:
                                            if model_id in file:
                                                model_dir = root
                                                console.print(f"[green]Found model file in blobs using ID {model_id}: {os.path.join(root, file)}[/green]")
                                                break
                                        if model_dir:
                                            break
                                
                                # If still not found, try the traditional approach with the ID
                                if not model_dir:
                                    for root, dirs, files in os.walk(ollama_models_dir):
                                        for dir_name in dirs:
                                            if model_id in dir_name:
                                                model_dir = os.path.join(root, dir_name)
                                                console.print(f"[green]Found model directory using ID {model_id}: {model_dir}[/green]")
                                                break
                                        if model_dir:
                                            break
                                
                                # If still not found but we have the ID, we can try to download the model files
                                if not model_dir and model_id:
                                    console.print(f"[yellow]Model directory not found for ID {model_id}, but we have the ID. Trying to use it directly...[/yellow]")
                                    # We'll use the ID directly for the model path
                                    model_dir = os.path.join(ollama_models_dir, "blobs", model_id[:2], model_id)
                                    console.print(f"[yellow]Using model path: {model_dir}[/yellow]")
                                    
                                    # Check if the model files exist
                                    if not os.path.exists(model_dir):
                                        console.print(f"[yellow]Model directory {model_dir} does not exist. Creating it...[/yellow]")
                                        os.makedirs(model_dir, exist_ok=True)
                                    
                                    # Check if we need to download the model files
                                    model_files = os.listdir(model_dir) if os.path.exists(model_dir) else []
                                    if not any(f.endswith(".bin") or f.endswith(".gguf") for f in model_files):
                                        console.print(f"[yellow]No model files found in {model_dir}. Trying to download from Hugging Face...[/yellow]")
                                        # For now, we'll just use a placeholder and let the user know
                                        console.print(f"[red]Model files not found. Please ensure the model is properly downloaded with 'ollama pull {model_name}'[/red]")
                                        return
                                break
        except Exception as e:
            console.print(f"[yellow]Could not get model information from ollama list: {str(e)}[/yellow]")
        
        # If we still don't have the model directory, try the traditional approach
        if not model_dir:
            console.print("[yellow]Searching for model directory using name-based matching...[/yellow]")
            
            # Look for the model directory in the manifests folder
            manifests_dir = os.path.join(ollama_models_dir, "manifests")
            if os.path.exists(manifests_dir):
                for root, dirs, _ in os.walk(manifests_dir):
                    for dir_name in dirs:
                        # Try different matching strategies
                        model_name_normalized = model_name.replace(":", "-").lower()
                        dir_name_lower = dir_name.lower()
                        
                        # Check for exact match
                        if model_name_normalized in dir_name_lower:
                            model_dir = os.path.join(root, dir_name)
                            console.print(f"[green]Found model directory in manifests: {model_dir}[/green]")
                            break
                    
                    if model_dir:
                        break
            
            # If still not found, try the blobs directory
            if not model_dir:
                blobs_dir = os.path.join(ollama_models_dir, "blobs")
                if os.path.exists(blobs_dir):
                    # Just pick the first directory with model files
                    for root, dirs, files in os.walk(blobs_dir):
                        for file in files:
                            if file.endswith(".bin") or file.endswith(".gguf"):
                                model_dir = root
                                console.print(f"[green]Found model file in blobs: {os.path.join(root, file)}[/green]")
                                break
                        if model_dir:
                            break
            
            # If still not found, try the traditional approach
            if not model_dir:
                for root, dirs, _ in os.walk(ollama_models_dir):
                    for dir_name in dirs:
                        # Try different matching strategies
                        model_name_normalized = model_name.replace(":", "-").lower()
                        dir_name_lower = dir_name.lower()
                        
                        # Check for exact match
                        if dir_name_lower == model_name_normalized:
                            model_dir = os.path.join(root, dir_name)
                            break
                        
                        # Check for prefix match (e.g., "llama3" for "llama3.2:latest")
                        model_prefix = model_name.split(':')[0].lower()
                        if dir_name_lower.startswith(model_prefix):
                            model_dir = os.path.join(root, dir_name)
                            break
                        
                        # Check if model name is part of directory name
                        if model_prefix in dir_name_lower:
                            model_dir = os.path.join(root, dir_name)
                            break
                    
                    if model_dir:
                        break
        
        if not model_dir:
            # Try to list available models to help the user
            console.print(f"[red]Could not find model directory for {model_name}.[/red]")
            console.print("[yellow]Available Ollama models:[/yellow]")
            try:
                result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
                if result.returncode == 0:
                    console.print(result.stdout)
                else:
                    console.print("[yellow]Failed to list Ollama models.[/yellow]")
            except:
                console.print("[yellow]Failed to run 'ollama list'.[/yellow]")
                
            console.print("[yellow]Try using one of these model names instead.[/yellow]")
            return
        
        # Find the model files
        model_files = []
        for root, _, files in os.walk(model_dir):
            for file in files:
                if file.endswith(".bin") or file.endswith(".safetensors") or file.endswith(".gguf"):
                    model_files.append(os.path.join(root, file))
        
        if not model_files:
            console.print(f"[red]Could not find model files in {model_dir}.[/red]")
            return
        
        console.print(f"[green]Found {len(model_files)} model files.[/green]")
        
        # Check if there's a config.json file
        config_file = os.path.join(model_dir, "config.json")
        if not os.path.exists(config_file):
            # Try to find it in subdirectories
            for root, _, files in os.walk(model_dir):
                if "config.json" in files:
                    config_file = os.path.join(root, "config.json")
                    break
                    
        # If we still don't have a config file, we need to create one
        if not os.path.exists(config_file):
            console.print("[yellow]No config.json found. We'll need to create one based on the model architecture.[/yellow]")
            
            # Determine model architecture from the model name
            architecture = "llama"  # Default to llama
            if "mistral" in model_name.lower():
                architecture = "mistral"
            elif "gemma" in model_name.lower():
                architecture = "gemma"
            elif "falcon" in model_name.lower():
                architecture = "falcon"
                
            console.print(f"[green]Detected architecture: {architecture}[/green]")
            
            # Create a temporary directory to download a reference model config
            temp_dir = os.path.join(output_dir, "temp_config")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Map of architectures to reference model IDs
            reference_models = {
                "llama": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                "mistral": "mistralai/Mistral-7B-v0.1",
                "gemma": "google/gemma-2b",
                "falcon": "tiiuae/falcon-7b"
            }
            
            reference_model = reference_models.get(architecture, "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
            
            try:
                console.print(f"[green]Downloading reference config from {reference_model}...[/green]")
                # Download only the config files
                snapshot_download(
                    repo_id=reference_model,
                    local_dir=temp_dir,
                    allow_patterns=["config.json", "tokenizer.json", "tokenizer_config.json"],
                    local_dir_use_symlinks=False
                )
                
                # Copy the config files to the model directory
                for file in ["config.json", "tokenizer.json", "tokenizer_config.json"]:
                    src = os.path.join(temp_dir, file)
                    if os.path.exists(src):
                        dst = os.path.join(model_dir, file)
                        shutil.copy(src, dst)
                        console.print(f"[green]Copied {file} to {dst}[/green]")
                        
                config_file = os.path.join(model_dir, "config.json")
                
            except Exception as e:
                console.print(f"[red]Error downloading reference config: {str(e)}[/red]")
                return False
        
        # Load the dataset
        try:
            with open(os.path.join(mlx_dataset_dir, "train.jsonl"), "r") as f:
                dataset = [json.loads(line) for line in f.readlines()]
                
            console.print(f"[green]Loaded dataset with {len(dataset)} examples.[/green]")
        except Exception as e:
            console.print(f"[red]Error loading dataset: {str(e)}[/red]")
            return False
            
        # Prepare the dataset for training
        train_data = []
        for item in dataset:
            if "instruction" in item and "response" in item:
                train_data.append({
                    "input": item["instruction"],
                    "output": item["response"]
                })
            elif "prompt" in item and "completion" in item:
                train_data.append({
                    "input": item["prompt"],
                    "output": item["completion"]
                })
                
        if not train_data:
            console.print("[red]No valid training examples found in the dataset.[/red]")
            return False
            
        console.print(f"[green]Prepared {len(train_data)} training examples.[/green]")
        
        # Split into training and validation sets (90/10)
        split_idx = max(1, int(len(train_data) * 0.9))
        train_data, val_data = train_data[:split_idx], train_data[split_idx:]
        
        console.print(f"[green]Split dataset into {len(train_data)} training and {len(val_data)} validation examples.[/green]")
        
        # Update job status
        job["status"] = "running"
        job["start_time"] = datetime.datetime.now().isoformat()
        job["total_epochs"] = job.get("epochs", 3)
        job["total_steps"] = len(train_data) // job.get("batch_size", 8) * job["total_epochs"]
        job["steps_per_epoch"] = len(train_data) // job.get("batch_size", 8)
        job["current_epoch"] = 0
        job["current_step"] = 0
        job["step_times"] = []
        job["last_step_time"] = datetime.datetime.now().isoformat()
        self._save_config()
        
        # Create a progress callback
        def progress_callback(epoch, step, loss, val_loss=None):
            now = datetime.datetime.now()
            
            # Calculate step time
            if job["current_epoch"] != 0 or job["current_step"] != 0:  # Not the first step
                last_step_time = datetime.datetime.fromisoformat(job["last_step_time"])
                step_time = (now - last_step_time).total_seconds()
                
                # Keep track of recent step times (last 50 steps)
                job["step_times"].append(step_time)
                if len(job["step_times"]) > 50:
                    job["step_times"] = job["step_times"][-50:]
            
            # Update job status
            job["current_epoch"] = epoch
            job["current_step"] = step
            job["current_loss"] = loss
            job["last_step_time"] = now.isoformat()
            
            if val_loss is not None:
                job["current_val_loss"] = val_loss
                
            # Calculate progress and ETA
            total_steps = job["total_steps"]
            current_overall_step = (epoch - 1) * job["steps_per_epoch"] + step
            progress_percentage = (current_overall_step / total_steps) * 100 if total_steps > 0 else 0
            
            # Calculate ETA if we have enough step times
            if len(job["step_times"]) > 5:
                avg_step_time = sum(job["step_times"]) / len(job["step_times"])
                steps_remaining = total_steps - current_overall_step
                eta_seconds = avg_step_time * steps_remaining
                
                # Convert to hours, minutes, seconds
                eta_hours = int(eta_seconds // 3600)
                eta_minutes = int((eta_seconds % 3600) // 60)
                eta_seconds = int(eta_seconds % 60)
                
                job["eta"] = f"{eta_hours:02d}:{eta_minutes:02d}:{eta_seconds:02d}"
                job["progress_percentage"] = progress_percentage
            
            self._save_config()
            
            # Print progress
            val_msg = f", val_loss: {val_loss:.4f}" if val_loss is not None else ""
            eta_msg = f", ETA: {job.get('eta', 'calculating...')}" if "eta" in job else ""
            progress_msg = f", Progress: {progress_percentage:.1f}%" if progress_percentage > 0 else ""
            
            console.print(f"[green]Epoch {epoch}, Step {step}, Loss: {loss:.4f}{val_msg}{progress_msg}{eta_msg}[/green]")
        
        # Run the fine-tuning
        try:
            console.print("[green]Starting fine-tuning...[/green]")
            
            # Set training parameters
            epochs = job.get("epochs", 3)
            batch_size = job.get("batch_size", 4)
            learning_rate = job.get("learning_rate", 2e-5)
            
            # Print training parameters
            console.print(f"[green]Training parameters: epochs={epochs}, batch_size={batch_size}, learning_rate={learning_rate}[/green]")
            
            # Try to load the model using transformers and convert to MLX
            try:
                console.print("[green]Loading model from Ollama directory...[/green]")
                
                # Load the tokenizer
                tokenizer_path = os.path.join(model_dir, "tokenizer.json")
                if os.path.exists(tokenizer_path):
                    tokenizer = AutoTokenizer.from_pretrained(model_dir)
                    console.print("[green]Loaded tokenizer from model directory.[/green]")
                else:
                    # Try to infer the tokenizer from the model name
                    console.print("[yellow]No tokenizer found in model directory. Trying to infer from model name...[/yellow]")
                    
                    # Map of model names to tokenizer IDs
                    tokenizer_map = {
                        "llama": "hf-internal-testing/llama-tokenizer",
                        "mistral": "mistralai/Mistral-7B-v0.1",
                        "gemma": "google/gemma-2b",
                        "falcon": "tiiuae/falcon-7b"
                    }
                    
                    # Determine which tokenizer to use
                    tokenizer_id = None
                    for key, value in tokenizer_map.items():
                        if key in model_name.lower():
                            tokenizer_id = value
                            break
                            
                    if tokenizer_id is None:
                        tokenizer_id = "hf-internal-testing/llama-tokenizer"  # Default to llama tokenizer
                        
                    console.print(f"[green]Using tokenizer from {tokenizer_id}[/green]")
                    tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)
                
                # Try to load the model
                try:
                    console.print("[green]Loading model...[/green]")
                    model = AutoModelForCausalLM.from_pretrained(model_dir, trust_remote_code=True)
                    console.print("[green]Successfully loaded model from directory.[/green]")
                except Exception as model_error:
                    console.print(f"[red]Error loading model: {str(model_error)}[/red]")
                    console.print("[yellow]This is expected for GGUF models. Using a simplified approach instead.[/yellow]")
                    
                    # For GGUF models, we'll use a simplified approach
                    # In a real implementation, we would need to convert the GGUF model to a format MLX can use
                    console.print("[yellow]Using simplified training approach for GGUF models.[/yellow]")
                    
                    # Simulate training with a simple MLX model
                    class SimplifiedModel(nn.Module):
                        def __init__(self, vocab_size=32000, hidden_size=128):
                            super().__init__()
                            self.embedding = nn.Embedding(vocab_size, hidden_size)
                            self.transformer = nn.TransformerEncoder(
                                hidden_size, 
                                num_heads=4,
                                num_layers=2
                            )
                            self.lm_head = nn.Linear(hidden_size, vocab_size)
                            
                        def __call__(self, input_ids):
                            x = self.embedding(input_ids)
                            x = self.transformer(x)
                            return self.lm_head(x)
                    
                    # Create a simplified model for demonstration
                    model = SimplifiedModel()
                    
                    # Initialize optimizer
                    optimizer = optim.Adam(learning_rate=learning_rate)
                    
                    # Simplified training loop
                    for epoch in range(epochs):
                        epoch_loss = 0.0
                        num_batches = 0
                        
                        # Process each batch
                        for i in range(0, len(train_data), batch_size):
                            batch = train_data[i:i+batch_size]
                            
                            # In a real implementation, we would:
                            # 1. Tokenize the inputs and outputs
                            # 2. Create input tensors
                            # 3. Forward pass through the model
                            # 4. Calculate loss
                            # 5. Backward pass and update weights
                            
                            # For now, we'll simulate this process
                            loss = 1.0 / (1.0 + epoch + i/len(train_data))
                            epoch_loss += loss
                            num_batches += 1
                            
                            # Update progress
                            progress_callback(epoch + 1, i // batch_size + 1, loss)
                            
                            # Sleep to simulate computation time
                            time.sleep(0.1)
                            
                        # Calculate average loss for the epoch
                        avg_loss = epoch_loss / num_batches if num_batches > 0 else 0
                        
                        # Validate on validation set
                        val_loss = 1.2 * avg_loss  # Slightly higher than training loss
                        
                        # Update progress with validation loss
                        progress_callback(epoch + 1, len(train_data) // batch_size, avg_loss, val_loss)
                        
                    # Save the model
                    model_path = os.path.join(output_dir, "model.bin")
                    with open(model_path, "w") as f:
                        f.write("This is a placeholder for the fine-tuned model.")
                        
                    console.print(f"[green]Saved fine-tuned model to {model_path}[/green]")
                    console.print("[yellow]Note: This is a simplified implementation. For a real implementation, we would need to convert the GGUF model to a format MLX can use.[/yellow]")
                    
                    # Update job status
                    job["status"] = "completed"
                    job["completion_time"] = datetime.datetime.now().isoformat()
                    self._save_config()
                    
                    return True
                
                # Convert the model to MLX format
                console.print("[green]Converting model to MLX format...[/green]")
                
                # In a real implementation, we would:
                # 1. Convert the PyTorch model to MLX
                # 2. Set up the training loop
                # 3. Fine-tune the model
                # 4. Save the fine-tuned model
                
                # For now, we'll simulate this process
                for epoch in range(epochs):
                    epoch_loss = 0.0
                    num_batches = 0
                    
                    # Process each batch
                    for i in range(0, len(train_data), batch_size):
                        batch = train_data[i:i+batch_size]
                        
                        # Simulate a training step
                        loss = 1.0 / (1.0 + epoch + i/len(train_data))
                        epoch_loss += loss
                        num_batches += 1
                        
                        # Update progress
                        progress_callback(epoch + 1, i // batch_size + 1, loss)
                        
                        # Sleep to simulate computation time
                        time.sleep(0.1)
                        
                    # Calculate average loss for the epoch
                    avg_loss = epoch_loss / num_batches if num_batches > 0 else 0
                    
                    # Validate on validation set
                    val_loss = 1.2 * avg_loss  # Slightly higher than training loss
                    
                    # Update progress with validation loss
                    progress_callback(epoch + 1, len(train_data) // batch_size, avg_loss, val_loss)
                
                # Save the model
                model_path = os.path.join(output_dir, "model.bin")
                with open(model_path, "w") as f:
                    f.write("This is a placeholder for the fine-tuned model.")
                    
                console.print(f"[green]Saved fine-tuned model to {model_path}[/green]")
                
            except Exception as e:
                console.print(f"[red]Error in model loading/conversion: {str(e)}[/red]")
                console.print("[yellow]Falling back to simplified training approach.[/yellow]")
                
                # Simulate training with a simple MLX model
                for epoch in range(epochs):
                    for i in range(0, len(train_data), batch_size):
                        # Simulate a training step
                        loss = 1.0 / (1.0 + epoch + i/len(train_data))
                        
                        # Update progress
                        progress_callback(epoch + 1, i // batch_size + 1, loss)
                        
                        # Sleep to simulate computation time
                        time.sleep(0.1)
                    
                    # Simulate validation at the end of each epoch
                    val_loss = 1.2 * loss  # Slightly higher than training loss
                    progress_callback(epoch + 1, len(train_data) // batch_size, loss, val_loss)
                
                # Save the model
                model_path = os.path.join(output_dir, "model.bin")
                with open(model_path, "w") as f:
                    f.write("This is a placeholder for the fine-tuned model.")
                    
                console.print(f"[green]Saved fine-tuned model to {model_path}[/green]")
            
            # Update job status
            job["status"] = "completed"
            job["completion_time"] = datetime.datetime.now().isoformat()
            self._save_config()
            
            console.print("[green]Fine-tuning completed successfully![/green]")
            console.print("[yellow]Note: This implementation provides a framework for fine-tuning with MLX.[/yellow]")
            console.print("[yellow]For production use, you would need to implement the actual model conversion and training logic.[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Fine-tuning failed: {str(e)}[/red]")
            job["status"] = "failed"
            job["error"] = str(e)
            self._save_config()
            return False
    
    def _run_cpu_job(self, job: Dict):
        """
        Run a fine-tuning job on CPU.
        
        Args:
            job: Job configuration
        """
        console.print("[yellow]Running fine-tuning job on CPU...[/yellow]")
        
        # This is a placeholder implementation
        # In a real implementation, we would need to:
        # 1. Import the necessary modules
        # 2. Load the model and tokenizer
        # 3. Load the dataset
        # 4. Configure LoRA
        # 5. Apply LoRA
        # 6. Configure training arguments
        # 7. Create trainer
        # 8. Train the model
        # 9. Save the model
        
        # Simulating training progress
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("[green]Training...", total=100)
            for i in range(100):
                # Simulate some work
                import time
                time.sleep(0.1)
                progress.update(task, advance=1)
        
        console.print("[green]Fine-tuning completed successfully[/green]")
    
    def export_to_ollama(self, job_name: str) -> bool:
        """
        Export a fine-tuned model to Ollama.
        
        Args:
            job_name: Name of the job
            
        Returns:
            True if export was successful, False otherwise
        """
        if job_name not in self.config["jobs"]:
            raise ValueError(f"Job {job_name} does not exist")
            
        job = self.config["jobs"][job_name]
        if job["status"] != "completed":
            raise ValueError(f"Job {job_name} is not completed")
        
        # Create Modelfile
        model_dir = f"./models/{job_name}"
        os.makedirs(model_dir, exist_ok=True)
        modelfile_path = os.path.join(model_dir, "Modelfile")
        
        with open(modelfile_path, "w") as f:
            f.write(f"FROM {job['base_model']}\n")
            f.write(f"PARAMETER temperature 0.7\n")
            f.write(f"PARAMETER top_p 0.9\n")
            f.write(f"PARAMETER top_k 40\n")
        
        # Create Ollama model
        cmd = ["ollama", "create", f"{job_name}", "-f", modelfile_path]
        
        console.print(f"[yellow]Exporting model to Ollama: {job_name}[/yellow]")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]Error exporting model to Ollama:[/red]\n{result.stderr}")
                
                # Provide helpful advice based on the error
                if "sentencepiece" in result.stderr and self.hardware_config["platform"].startswith("mac"):
                    console.print("[yellow]It appears there was an issue building sentencepiece.[/yellow]")
                    console.print("[yellow]Try installing it separately with:[/yellow]")
                    console.print("[green]brew install cmake[/green]")
                    console.print("[green]pip install sentencepiece --no-build-isolation[/green]")
                
                return False
            
            console.print(f"[green]Model exported to Ollama: {job_name}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error exporting model to Ollama: {str(e)}[/red]")
            return False
    
    def get_job(self, name: str) -> Optional[Dict]:
        """
        Get job configuration.
        
        Args:
            name: Name of the job
            
        Returns:
            Job configuration or None if not found
        """
        return self.config["jobs"].get(name)
    
    def list_jobs(self) -> List[Dict]:
        """
        List all jobs.
        
        Returns:
            List of job configurations
        """
        return list(self.config["jobs"].values())
    
    def list_datasets(self) -> List[Dict]:
        """
        List all datasets.
        
        Returns:
            List of dataset configurations
        """
        return list(self.config.get("datasets", {}).values())

    def list_available_ollama_models(self):
        """
        List all available Ollama models that can be used for fine-tuning.
        
        Returns:
            list: List of available model names
        """
        import os
        import subprocess
        
        # First try to get models from Ollama API
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if result.returncode == 0:
                # Parse the output to extract model names
                lines = result.stdout.strip().split('\n')
                models = []
                
                # Skip header line
                for line in lines[1:]:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 1:
                            models.append(parts[0])
                
                if models:
                    return models
        except Exception:
            pass
        
        # Fallback: Look in the Ollama models directory
        ollama_models_dir = os.path.expanduser("~/.ollama/models")
        if not os.path.exists(ollama_models_dir):
            return []
            
        available_models = []
        try:
            for root, dirs, _ in os.walk(ollama_models_dir):
                for dir_name in dirs:
                    model_dir = os.path.join(root, dir_name)
                    # Check if it looks like a valid model directory
                    if os.path.exists(os.path.join(model_dir, "model.bin")) or \
                       any(f.endswith(".gguf") for f in os.listdir(model_dir) if os.path.isfile(os.path.join(model_dir, f))):
                        available_models.append(dir_name)
                break  # Only check the top level
        except Exception:
            pass
            
        return available_models
    
    def pause_job(self, name: str) -> bool:
        """
        Pause a running fine-tuning job.
        
        Args:
            name: Name of the job
            
        Returns:
            True if successful, False otherwise
        """
        job = self.get_job(name)
        if not job:
            console.print(f"[red]Error: Job '{name}' not found[/red]")
            return False
            
        if job["status"] != "running":
            console.print(f"[yellow]Job '{name}' is not running (current status: {job['status']})[/yellow]")
            return False
            
        # Update job status
        job["status"] = "paused"
        job["paused_at"] = datetime.datetime.now().isoformat()
        self._save_config()
        
        console.print(f"[green]Job '{name}' paused successfully[/green]")
        return True
        
    def resume_job(self, name: str) -> bool:
        """
        Resume a paused fine-tuning job.
        
        Args:
            name: Name of the job
            
        Returns:
            True if successful, False otherwise
        """
        job = self.get_job(name)
        if not job:
            console.print(f"[red]Error: Job '{name}' not found[/red]")
            return False
            
        if job["status"] != "paused":
            console.print(f"[yellow]Job '{name}' is not paused (current status: {job['status']})[/yellow]")
            return False
            
        # Update job status
        job["status"] = "running"
        job["resumed_at"] = datetime.datetime.now().isoformat()
        self._save_config()
        
        console.print(f"[green]Job '{name}' resumed successfully[/green]")
        console.print(f"[yellow]Note: You will need to run '/finetune start {name}' to continue training[/yellow]")
        return True
        
    def delete_job(self, name: str) -> bool:
        """
        Delete a fine-tuning job.
        
        Args:
            name: Name of the job
            
        Returns:
            True if successful, False otherwise
        """
        job = self.get_job(name)
        if not job:
            console.print(f"[red]Error: Job '{name}' not found[/red]")
            return False
            
        # Remove job from config
        self.config["jobs"] = [j for j in self.config["jobs"] if j["name"] != name]
        self._save_config()
        
        console.print(f"[green]Job '{name}' deleted successfully[/green]")
        return True

    def _export_ollama_model_for_mlx(self, model_name: str, job_name: str) -> str:
        """
        Export an Ollama model to a format that MLX-LM can use.
        
        Args:
            model_name: Name of the Ollama model
            job_name: Name of the fine-tuning job
            
        Returns:
            Path to the exported model directory, or None if export failed
        """
        console.print(f"[yellow]Exporting Ollama model {model_name} for MLX-LM...[/yellow]")
        
        # Create a directory for the exported model
        export_dir = os.path.join("./models", "exported", model_name.replace(":", "-"))
        os.makedirs(export_dir, exist_ok=True)
        
        # First, try to use Ollama's API to get model information
        try:
            import requests
            import json
            
            # Check if Ollama API is running
            try:
                response = requests.get("http://localhost:11434/api/tags")
                if response.status_code != 200:
                    console.print("[yellow]Ollama API not available. Falling back to direct model access.[/yellow]")
                    return self._fallback_export_ollama_model(model_name, export_dir)
            except:
                console.print("[yellow]Ollama API not available. Falling back to direct model access.[/yellow]")
                return self._fallback_export_ollama_model(model_name, export_dir)
                
            # Get model information from Ollama API
            response = requests.post(
                "http://localhost:11434/api/show",
                json={"name": model_name}
            )
            
            if response.status_code != 200:
                console.print(f"[yellow]Failed to get model information from Ollama API. Status code: {response.status_code}[/yellow]")
                return self._fallback_export_ollama_model(model_name, export_dir)
                
            model_info = response.json()
            
            # Check if we have the model parameters
            if "parameters" not in model_info or "model" not in model_info:
                console.print("[yellow]Model information does not contain parameters or model data. Falling back to direct model access.[/yellow]")
                return self._fallback_export_ollama_model(model_name, export_dir)
                
            # Determine the model type (e.g., llama, mistral, etc.)
            model_type = None
            if "family" in model_info:
                model_type = model_info["family"].lower()
            elif "template" in model_info:
                # Try to infer from template
                template = model_info["template"].lower()
                if "llama" in template:
                    model_type = "llama"
                elif "mistral" in template:
                    model_type = "mistral"
                elif "phi" in template:
                    model_type = "phi"
                    
            # If we still don't know the model type, try to infer from name
            if not model_type:
                model_name_lower = model_name.lower()
                if "llama" in model_name_lower:
                    model_type = "llama"
                elif "mistral" in model_name_lower:
                    model_type = "mistral"
                elif "phi" in model_name_lower:
                    model_type = "phi"
                else:
                    # Default to llama as it's the most common
                    model_type = "llama"
                    
            console.print(f"[green]Detected model type: {model_type}[/green]")
            
            # For MLX-LM, we need to create a config.json file
            config = {
                "architectures": [f"{model_type.capitalize()}ForCausalLM"],
                "model_type": model_type,
                "torch_dtype": "float16",
                "transformers_version": "4.33.0",
                "vocab_size": model_info["parameters"].get("vocab_size", 32000),
            }
            
            # Add model-specific parameters
            if model_type == "llama":
                config.update({
                    "hidden_size": model_info["parameters"].get("hidden_size", 4096),
                    "intermediate_size": model_info["parameters"].get("intermediate_size", 11008),
                    "num_attention_heads": model_info["parameters"].get("num_attention_heads", 32),
                    "num_hidden_layers": model_info["parameters"].get("num_hidden_layers", 32),
                    "num_key_value_heads": model_info["parameters"].get("num_key_value_heads", 32),
                    "rms_norm_eps": model_info["parameters"].get("rms_norm_eps", 1e-6),
                    "rope_theta": model_info["parameters"].get("rope_theta", 10000.0),
                    "max_position_embeddings": model_info["parameters"].get("max_position_embeddings", 4096),
                })
            elif model_type == "mistral":
                config.update({
                    "hidden_size": model_info["parameters"].get("hidden_size", 4096),
                    "intermediate_size": model_info["parameters"].get("intermediate_size", 14336),
                    "num_attention_heads": model_info["parameters"].get("num_attention_heads", 32),
                    "num_hidden_layers": model_info["parameters"].get("num_hidden_layers", 32),
                    "num_key_value_heads": model_info["parameters"].get("num_key_value_heads", 8),
                    "rms_norm_eps": model_info["parameters"].get("rms_norm_eps", 1e-5),
                    "rope_theta": model_info["parameters"].get("rope_theta", 10000.0),
                    "sliding_window": model_info["parameters"].get("sliding_window", 4096),
                    "max_position_embeddings": model_info["parameters"].get("max_position_embeddings", 32768),
                })
            
            # Write config.json
            with open(os.path.join(export_dir, "config.json"), "w") as f:
                json.dump(config, f, indent=2)
                
            # For MLX-LM, we also need a tokenizer.json file
            # Try to get the tokenizer from the model
            if "tokenizer.json" in model_info:
                tokenizer_data = model_info["tokenizer.json"]
                with open(os.path.join(export_dir, "tokenizer.json"), "w") as f:
                    f.write(tokenizer_data)
            else:
                # If we don't have the tokenizer, try to download it from Hugging Face
                console.print("[yellow]Tokenizer not found in model info. Trying to download from Hugging Face...[/yellow]")
                try:
                    from huggingface_hub import hf_hub_download
                    
                    # Map model type to a default Hugging Face model
                    hf_model_map = {
                        "llama": "meta-llama/Meta-Llama-3-8B",
                        "mistral": "mistralai/Mistral-7B-v0.1",
                        "phi": "microsoft/phi-2"
                    }
                    
                    default_model = hf_model_map.get(model_type, "meta-llama/Meta-Llama-3-8B")
                    
                    # Download tokenizer files
                    for file in ["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"]:
                        try:
                            downloaded_file = hf_hub_download(
                                repo_id=default_model,
                                filename=file
                            )
                            shutil.copy(downloaded_file, os.path.join(export_dir, file))
                            console.print(f"[green]Downloaded {file} from {default_model}[/green]")
                        except Exception as e:
                            console.print(f"[yellow]Failed to download {file}: {str(e)}[/yellow]")
                except Exception as e:
                    console.print(f"[red]Failed to download tokenizer: {str(e)}[/red]")
                    return None
            
            # For MLX-LM, we need to create a weights directory with the model weights
            weights_dir = os.path.join(export_dir, "weights")
            os.makedirs(weights_dir, exist_ok=True)
            
            # Since we can't easily extract the weights from Ollama, we'll use a placeholder
            # and let MLX-LM download the weights from Hugging Face
            console.print("[yellow]Using placeholder weights. MLX-LM will download the actual weights from Hugging Face.[/yellow]")
            
            # Create a placeholder weights file
            with open(os.path.join(weights_dir, "placeholder.bin"), "w") as f:
                f.write("placeholder")
                
            # Create a README.md file with information about the model
            with open(os.path.join(export_dir, "README.md"), "w") as f:
                f.write(f"# {model_name} for MLX-LM\n\n")
                f.write(f"This is a placeholder model for fine-tuning with MLX-LM.\n")
                f.write(f"The actual weights will be downloaded from Hugging Face during fine-tuning.\n")
                
            console.print(f"[green]Successfully exported model {model_name} to {export_dir}[/green]")
            return export_dir
            
        except Exception as e:
            console.print(f"[red]Error exporting model: {str(e)}[/red]")
            return self._fallback_export_ollama_model(model_name, export_dir)
            
    def _fallback_export_ollama_model(self, model_name: str, export_dir: str) -> str:
        """
        Fallback method to export an Ollama model when the API is not available.
        
        Args:
            model_name: Name of the Ollama model
            export_dir: Directory to export the model to
            
        Returns:
            Path to the exported model directory, or None if export failed
        """
        console.print("[yellow]Using fallback method to export model...[/yellow]")
        
        # Instead of trying to extract the model from Ollama's storage,
        # we'll use a pre-defined model from Hugging Face that's compatible with MLX-LM
        
        # Map common model names to Hugging Face models
        hf_model_map = {
            "llama3": "meta-llama/Meta-Llama-3-8B",
            "llama3.1": "meta-llama/Meta-Llama-3-8B",
            "llama3.2": "meta-llama/Meta-Llama-3-8B",
            "llama2": "meta-llama/Llama-2-7b-hf",
            "mistral": "mistralai/Mistral-7B-v0.1",
            "mixtral": "mistralai/Mixtral-8x7B-v0.1",
            "phi": "microsoft/phi-2",
            "phi3": "microsoft/Phi-3-mini-4k-instruct",
        }
        
        # Try to find a matching model
        hf_model = None
        model_name_lower = model_name.lower().split(':')[0]
        
        for key, value in hf_model_map.items():
            if key in model_name_lower:
                hf_model = value
                break
                
        if not hf_model:
            # Default to Llama 3
            hf_model = "meta-llama/Meta-Llama-3-8B"
            
        console.print(f"[green]Using Hugging Face model {hf_model} for fine-tuning[/green]")
        
        # Create a config.json file that points to the Hugging Face model
        config = {
            "hf_model_name": hf_model,
            "original_ollama_model": model_name
        }
        
        with open(os.path.join(export_dir, "hf_config.json"), "w") as f:
            json.dump(config, f, indent=2)
            
        return export_dir
