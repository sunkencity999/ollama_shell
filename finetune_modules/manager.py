"""
Fine-tuning manager for Ollama Shell.
This module provides the main manager class for fine-tuning language models.
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

from .hardware_detection import detect_hardware
from .venv_utils import ensure_venv_exists, is_module_installed, install_dependencies
from .model_utils import get_ollama_models, get_ollama_model_path
from .dataset_utils import prepare_dataset

try:
    from rich.console import Console
    from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
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


class FineTuningManager:
    """Manager for fine-tuning language models."""
    
    def get_created_files_dir(self):
        """
        Get the path to the Created Files directory.
        
        Returns:
            Path to the Created Files directory
        """
        created_files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Created Files")
        os.makedirs(created_files_dir, exist_ok=True)
        return created_files_dir
    
    def __init__(self, config_path: str = None):
        """
        Initialize the fine-tuning manager.
        
        Args:
            config_path: Path to the configuration file (optional)
        """
        # Create the Created Files directory if it doesn't exist
        created_files_dir = self.get_created_files_dir()
        
        # Use the provided config path or default to one in the Created Files directory
        if config_path is None:
            config_path = os.path.join(created_files_dir, "finetune_config.json")
            
        self.config_path = config_path
        self.config = self._load_config()
        
        # Scan for jobs and datasets in the Created Files directory
        self._scan_created_files_directory()
        
        # Ensure virtual environment exists
        self.venv_path = ensure_venv_exists()
        
        # Detect hardware
        self.hardware_config = detect_hardware()
        console.print(f"[green]Detected hardware: {self.hardware_config['platform']}[/green]")
        console.print(f"[green]Using framework: {self.hardware_config['framework']}[/green]")
    
    def _load_config(self) -> Dict:
        """
        Load the configuration from the config file.
        
        Returns:
            Configuration dictionary
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                console.print(f"[red]Error parsing config file {self.config_path}[/red]")
                return {"jobs": {}, "datasets": {}}
        else:
            return {"jobs": {}, "datasets": {}}
    
    def _save_config(self):
        """Save the configuration to the config file."""
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)
            
    def _scan_created_files_directory(self):
        """Scan the Created Files directory for jobs and datasets that aren't in the config."""
        created_files_dir = self.get_created_files_dir()
        
        # Scan for jobs
        jobs_dir = os.path.join(created_files_dir, "jobs")
        if os.path.exists(jobs_dir) and os.path.isdir(jobs_dir):
            for job_name in os.listdir(jobs_dir):
                job_dir = os.path.join(jobs_dir, job_name)
                if os.path.isdir(job_dir) and job_name not in self.config.get("jobs", {}):
                    # Found a job directory that's not in the config
                    model_dir = os.path.join(job_dir, "model")
                    model_name_file = os.path.join(model_dir, "model_name.txt")
                    base_model = "unknown"
                    
                    if os.path.exists(model_name_file):
                        try:
                            with open(model_name_file, "r") as f:
                                base_model = f.read().strip()
                        except:
                            pass
                    
                    # Determine job status
                    status = "unknown"
                    if os.path.exists(os.path.join(job_dir, "completed")):
                        status = "completed"
                    elif os.path.exists(os.path.join(job_dir, "process.pid")):
                        # Check if process is still running
                        try:
                            with open(os.path.join(job_dir, "process.pid"), "r") as f:
                                pid = int(f.read().strip())
                            
                            # Try to check if process exists
                            try:
                                os.kill(pid, 0)  # Signal 0 doesn't kill the process, just checks if it exists
                                status = "running"
                            except ProcessLookupError:
                                status = "failed"
                        except:
                            status = "failed"
                    
                    # Add the job to the config
                    if "jobs" not in self.config:
                        self.config["jobs"] = {}
                    
                    self.config["jobs"][job_name] = {
                        "name": job_name,
                        "base_model": base_model,
                        "directory": job_dir,
                        "job_dir": job_dir,
                        "status": status,
                        "created_at": time.time()
                    }
        
        # Scan for datasets
        datasets_dir = os.path.join(created_files_dir, "datasets")
        if os.path.exists(datasets_dir) and os.path.isdir(datasets_dir):
            for dataset_name in os.listdir(datasets_dir):
                dataset_path = os.path.join(datasets_dir, dataset_name)
                
                # Skip if already in config
                if dataset_name in self.config.get("datasets", {}):
                    continue
                
                # Check if this is a directory or a file
                if os.path.isdir(dataset_path):
                    # Look for jsonl files in the directory
                    jsonl_files = [f for f in os.listdir(dataset_path) if f.endswith('.jsonl')]
                    
                    if jsonl_files:
                        # Add dataset to config
                        if "datasets" not in self.config:
                            self.config["datasets"] = {}
                            
                        self.config["datasets"][dataset_name] = {
                            "name": dataset_name,
                            "path": os.path.join(dataset_path, jsonl_files[0]),
                            "original_path": dataset_path,
                            "created_at": time.time()
                        }
                elif dataset_name.endswith('.jsonl') or dataset_name.endswith('.json'):
                    # This is a dataset file
                    dataset_id = os.path.splitext(dataset_name)[0]
                    
                    # Add dataset to config
                    if "datasets" not in self.config:
                        self.config["datasets"] = {}
                        
                    self.config["datasets"][dataset_id] = {
                        "path": dataset_path,
                        "original_path": dataset_path,
                        "created_at": time.time()
                    }
        
        # Save the updated config
        self._save_config()
    
    def check_dependencies(self) -> bool:
        """
        Check if required dependencies are installed.
        
        Returns:
            True if all dependencies are installed, False otherwise
        """
        framework = self.hardware_config["framework"]
        
        if framework == "mlx":
            # Check for MLX dependencies
            return (
                is_module_installed("mlx") and
                is_module_installed("mlx_lm") and
                is_module_installed("transformers") and
                is_module_installed("datasets")
            )
        elif framework in ["unsloth", "unsloth_windows"]:
            # Check for Unsloth dependencies
            return (
                is_module_installed("unsloth") and
                is_module_installed("transformers") and
                is_module_installed("datasets") and
                is_module_installed("peft") and
                is_module_installed("accelerate")
            )
        else:
            # CPU fallback
            return (
                is_module_installed("transformers") and
                is_module_installed("datasets")
            )
    
    def install_dependencies(self) -> bool:
        """
        Install required dependencies.
        
        Returns:
            True if installation was successful, False otherwise
        """
        return install_dependencies(self.hardware_config)
    
    def prepare_dataset(self, dataset_path: str, name: Optional[str] = None) -> Optional[str]:
        """
        Prepare a dataset for fine-tuning.
        
        Args:
            dataset_path: Path to the dataset file or directory
            name: Optional name for the dataset
            
        Returns:
            Dataset ID if successful, None otherwise
        """
        # Validate the dataset path
        if not os.path.exists(dataset_path):
            console.print(f"[red]Dataset not found at {dataset_path}[/red]")
            return None
        
        # Generate a dataset ID if not provided
        dataset_id = name or f"dataset_{int(time.time())}"
        
        # Create a directory for the dataset in the "Created Files" directory
        created_files_dir = self.get_created_files_dir()
        
        datasets_dir = os.path.join(created_files_dir, "datasets")
        os.makedirs(datasets_dir, exist_ok=True)
        
        dataset_dir = os.path.join(datasets_dir, dataset_id)
        os.makedirs(dataset_dir, exist_ok=True)
        
        # Prepare the dataset
        framework = self.hardware_config["framework"]
        prepared_path = prepare_dataset(dataset_path, dataset_dir, framework)
        
        if not prepared_path:
            console.print(f"[red]Failed to prepare dataset from {dataset_path}[/red]")
            return None
        
        # Add the dataset to the configuration
        if "datasets" not in self.config:
            self.config["datasets"] = {}
        
        self.config["datasets"][dataset_id] = {
            "path": prepared_path,
            "original_path": dataset_path,
            "created_at": time.time()
        }
        
        self._save_config()
        
        console.print(f"[green]Dataset prepared and saved as {dataset_id}[/green]")
        return dataset_id
    
    def get_datasets(self) -> Dict[str, Dict]:
        """
        Get all datasets.
        
        Returns:
            Dictionary of dataset ID to dataset information
        """
        return self.config.get("datasets", {})
    
    def get_latest_dataset(self) -> Optional[str]:
        """
        Get the ID of the latest dataset.
        
        Returns:
            Dataset ID or None if no datasets exist
        """
        datasets = self.get_datasets()
        if not datasets:
            return None
        
        # Find the dataset with the latest created_at timestamp
        latest_dataset = max(datasets.items(), key=lambda x: x[1].get("created_at", 0))
        return latest_dataset[0]
    
    def create_job(self, name: str, base_model: str, dataset_id: Optional[str] = None, parameters: Optional[Dict] = None) -> bool:
        """
        Create a fine-tuning job.
        
        Args:
            name: Name of the job
            base_model: Base model to fine-tune
            dataset_id: Dataset ID to use (optional, will use latest if not provided)
            parameters: Fine-tuning parameters (optional)
            
        Returns:
            True if the job was created successfully, False otherwise
        """
        # Check if a job with this name already exists
        if "jobs" in self.config and name in self.config["jobs"]:
            console.print(f"[red]A job with the name {name} already exists.[/red]")
            return False
        
        # If no dataset ID is provided, use the latest dataset
        if not dataset_id:
            dataset_id = self.get_latest_dataset()
            if not dataset_id:
                console.print("[red]No datasets available. Please prepare a dataset first.[/red]")
                return False
        
        # Check if the dataset exists
        if "datasets" not in self.config or dataset_id not in self.config["datasets"]:
            console.print(f"[red]Dataset {dataset_id} not found.[/red]")
            return False
        
        # Create a directory for the job in the "Created Files" directory
        created_files_dir = self.get_created_files_dir()
        
        jobs_dir = os.path.join(created_files_dir, "jobs")
        os.makedirs(jobs_dir, exist_ok=True)
        
        job_dir = os.path.join(jobs_dir, name)
        os.makedirs(job_dir, exist_ok=True)
        
        # Set default parameters based on the framework
        default_parameters = {
            "learning_rate": 2e-4,
            "per_device_train_batch_size": 2,
            "max_steps": 100,
            "weight_decay": 0.01
        }
        
        # Update with user-provided parameters
        if parameters:
            default_parameters.update(parameters)
        
        # Create the job configuration
        job = {
            "name": name,
            "base_model": base_model,
            "dataset_id": dataset_id,
            "dataset_path": self.config["datasets"][dataset_id]["path"],
            "parameters": default_parameters,
            "status": "created",
            "created_at": time.time(),
            "job_dir": job_dir
        }
        
        # Add the job to the configuration
        if "jobs" not in self.config:
            self.config["jobs"] = {}
        
        self.config["jobs"][name] = job
        self._save_config()
        
        console.print(f"[green]Created fine-tuning job {name}[/green]")
        return True
    
    def get_jobs(self) -> Dict[str, Dict]:
        """
        Get all jobs.
        
        Returns:
            Dictionary of job name to job information
        """
        return self.config.get("jobs", {})
    
    def get_job(self, name: str) -> Optional[Dict]:
        """
        Get a specific job.
        
        Args:
            name: Name of the job
            
        Returns:
            Job information or None if not found
        """
        return self.config.get("jobs", {}).get(name)
    
    def start_job(self, name: str) -> bool:
        """
        Start a fine-tuning job.
        
        Args:
            name: Name of the job
            
        Returns:
            True if the job was started successfully, False otherwise
        """
        # Check if the job exists
        job = self.get_job(name)
        if not job:
            console.print(f"[red]Job {name} not found.[/red]")
            return False
        
        # Check if the job is already running
        if job.get("status") == "running":
            console.print(f"[yellow]Job {name} is already running.[/yellow]")
            return True
        
        # Check if dependencies are installed
        if not self.check_dependencies():
            console.print("[red]Required dependencies are not installed.[/red]")
            console.print("[yellow]Please run /finetune install first.[/yellow]")
            return False
        
        # Get the job directory
        job_dir = job.get("job_dir")
        if not job_dir or not os.path.exists(job_dir):
            console.print(f"[red]Job directory for {name} not found.[/red]")
            return False
        
        # Start the job based on the framework
        framework = self.hardware_config["framework"]
        
        if framework == "mlx":
            # Import the MLX runner
            from .mlx_runner import run_mlx_lm
            
            # Start the MLX job
            success = run_mlx_lm(job, job_dir)
        elif framework in ["unsloth", "unsloth_windows"]:
            # Import the Unsloth runner
            from .unsloth_runner import run_unsloth
            
            # Start the Unsloth job
            success = run_unsloth(job, job_dir)
        else:
            console.print(f"[red]Unsupported framework: {framework}[/red]")
            return False
        
        if success:
            # Update the job status
            job["status"] = "running"
            job["start_time"] = time.time()
            self._save_config()
            
            console.print(f"[green]Started fine-tuning job {name}[/green]")
            return True
        else:
            console.print(f"[red]Failed to start fine-tuning job {name}[/red]")
            return False
    
    def check_job_status(self, name: str) -> Tuple[str, float, Optional[str]]:
        """
        Check the status of a fine-tuning job.
        
        Args:
            name: Name of the job
            
        Returns:
            Tuple of (status, progress, error_message)
        """
        # Check if the job exists
        job = self.get_job(name)
        if not job:
            return "not_found", 0.0, f"Job {name} not found"
        
        # If the job is not running, return its status
        if job.get("status") != "running":
            return job.get("status", "unknown"), 0.0, None
        
        # Get the job directory
        job_dir = job.get("job_dir")
        if not job_dir or not os.path.exists(job_dir):
            return "error", 0.0, f"Job directory for {name} not found"
        
        # Check the status based on the framework
        framework = self.hardware_config["framework"]
        
        if framework == "mlx":
            # Import the MLX runner
            from .mlx_runner import check_mlx_job_status
            
            # Check the MLX job status
            status, progress, error = check_mlx_job_status(job, job_dir)
        elif framework in ["unsloth", "unsloth_windows"]:
            # Import the Unsloth runner
            from .unsloth_runner import check_unsloth_job_status
            
            # Check the Unsloth job status
            status, progress, error = check_unsloth_job_status(job, job_dir)
        else:
            return "error", 0.0, f"Unsupported framework: {framework}"
        
        # Update the job status in the config
        if status != "running":
            job["status"] = status
            if status == "completed":
                job["completed_at"] = time.time()
            self._save_config()
        
        return status, progress, error
    
    def pause_job(self, name: str) -> bool:
        """
        Pause a running fine-tuning job.
        
        Args:
            name: Name of the job
            
        Returns:
            True if the job was paused successfully, False otherwise
        """
        # Check if the job exists
        job = self.get_job(name)
        if not job:
            console.print(f"[red]Job {name} not found.[/red]")
            return False
        
        # Check if the job is running
        if job.get("status") != "running":
            console.print(f"[yellow]Job {name} is not running (status: {job.get('status')}).[/yellow]")
            return False
        
        # Get the process ID
        pid = job.get("pid")
        if not pid:
            console.print(f"[red]No process ID found for job {name}.[/red]")
            return False
        
        try:
            # Send SIGSTOP to pause the process
            import signal
            os.kill(pid, signal.SIGSTOP)
            
            # Update the job status
            job["status"] = "paused"
            job["paused_at"] = time.time()
            self._save_config()
            
            console.print(f"[green]Paused fine-tuning job {name}[/green]")
            return True
        except ProcessLookupError:
            console.print(f"[red]Process for job {name} not found.[/red]")
            
            # Update the job status to failed
            job["status"] = "failed"
            self._save_config()
            
            return False
        except Exception as e:
            console.print(f"[red]Error pausing job {name}: {str(e)}[/red]")
            return False
    
    def resume_job(self, name: str) -> bool:
        """
        Resume a paused fine-tuning job.
        
        Args:
            name: Name of the job
            
        Returns:
            True if the job was resumed successfully, False otherwise
        """
        # Check if the job exists
        job = self.get_job(name)
        if not job:
            console.print(f"[red]Job {name} not found.[/red]")
            return False
        
        # Check if the job is paused
        if job.get("status") != "paused":
            console.print(f"[yellow]Job {name} is not paused (status: {job.get('status')}).[/yellow]")
            return False
        
        # Get the process ID
        pid = job.get("pid")
        if not pid:
            console.print(f"[red]No process ID found for job {name}.[/red]")
            return False
        
        try:
            # Send SIGCONT to resume the process
            import signal
            os.kill(pid, signal.SIGCONT)
            
            # Update the job status
            job["status"] = "running"
            job["resumed_at"] = time.time()
            self._save_config()
            
            console.print(f"[green]Resumed fine-tuning job {name}[/green]")
            return True
        except ProcessLookupError:
            console.print(f"[red]Process for job {name} not found.[/red]")
            
            # Update the job status to failed
            job["status"] = "failed"
            self._save_config()
            
            return False
        except Exception as e:
            console.print(f"[red]Error resuming job {name}: {str(e)}[/red]")
            return False
    
    def reset_job(self, name: str) -> bool:
        """
        Reset a fine-tuning job to the 'created' state so it can be restarted.
        
        Args:
            name: Name of the job
            
        Returns:
            True if the job was reset successfully, False otherwise
        """
        import signal
        # Check if the job exists
        job = self.get_job(name)
        if not job:
            console.print(f"[red]Job {name} not found.[/red]")
            return False
        
        # Check if the job is running and try to stop it
        if job.get("status") == "running":
            try:
                pid = job.get("pid")
                if pid:
                    try:
                        os.kill(pid, signal.SIGTERM)
                        console.print(f"[yellow]Terminated running process for job {name}.[/yellow]")
                    except ProcessLookupError:
                        console.print(f"[yellow]Process for job {name} not found, continuing with reset.[/yellow]")
                    except Exception as e:
                        console.print(f"[yellow]Error terminating process for job {name}: {str(e)}[/yellow]")
            except Exception as e:
                console.print(f"[yellow]Error stopping job {name}: {str(e)}[/yellow]")
        
        # Reset the job status and related fields
        job["status"] = "created"
        job.pop("pid", None)
        job.pop("start_time", None)
        job.pop("end_time", None)
        job.pop("paused_at", None)
        job.pop("resumed_at", None)
        job.pop("progress", None)
        
        # Clean up job directory if it exists
        job_dir = job.get("job_dir")
        if job_dir and os.path.exists(job_dir):
            try:
                # Remove output directory but keep the job directory itself
                output_dir = os.path.join(job_dir, "output")
                if os.path.exists(output_dir):
                    shutil.rmtree(output_dir)
                    console.print(f"[yellow]Removed output directory for job {name}.[/yellow]")
                
                # Remove any progress or completion files
                for filename in ["progress.json", "completed", "error.txt", "process.pid", "finetune.log"]:
                    file_path = os.path.join(job_dir, filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
            except Exception as e:
                console.print(f"[yellow]Error cleaning up job directory: {str(e)}[/yellow]")
        
        # Save the updated configuration
        self._save_config()
        
        console.print(f"[green]Reset fine-tuning job {name} to 'created' state.[/green]")
        return True
        
    def delete_job(self, name: str) -> bool:
        """
        Delete a fine-tuning job.
        
        Args:
            name: Name of the job
            
        Returns:
            True if the job was deleted successfully, False otherwise
        """
        # Check if the job exists
        job = self.get_job(name)
        if not job:
            console.print(f"[red]Job {name} not found.[/red]")
            return False
        
        # Check if the job is running
        if job.get("status") == "running":
            console.print(f"[yellow]Job {name} is still running. Please stop it first.[/yellow]")
            return False
        
        # Get the job directory
        job_dir = job.get("job_dir")
        if job_dir and os.path.exists(job_dir):
            # Remove the job directory
            try:
                shutil.rmtree(job_dir)
            except Exception as e:
                console.print(f"[red]Error removing job directory: {str(e)}[/red]")
        
        # Remove the job from the configuration
        if "jobs" in self.config and name in self.config["jobs"]:
            del self.config["jobs"][name]
            self._save_config()
        
        console.print(f"[green]Deleted fine-tuning job {name}[/green]")
        return True
    
    def update_job_dataset(self, job_name: str, dataset_id: str) -> bool:
        """
        Update the dataset for a fine-tuning job.
        
        Args:
            job_name: Name of the job
            dataset_id: ID of the dataset to use
            
        Returns:
            True if the job was updated successfully, False otherwise
        """
        # Check if the job exists
        job = self.get_job(job_name)
        if not job:
            console.print(f"[red]Job {job_name} not found.[/red]")
            return False
        
        # Check if the job is in a state where the dataset can be changed
        valid_states = ["created", "failed", "completed"]
        if job.get("status") not in valid_states:
            console.print(f"[yellow]Cannot change dataset for job in status: {job.get('status')}[/yellow]")
            console.print(f"[yellow]Job must be in one of these states: {', '.join(valid_states)}[/yellow]")
            return False
        
        # Check if the dataset exists
        datasets = self.get_datasets()
        if dataset_id not in datasets:
            console.print(f"[red]Dataset {dataset_id} not found.[/red]")
            console.print("[yellow]Use /finetune datasets to see available datasets.[/yellow]")
            return False
        
        # Update the job with the new dataset
        job["dataset_id"] = dataset_id
        job["dataset_path"] = datasets[dataset_id]["path"]
        
        # Save the configuration
        self._save_config()
        
        console.print(f"[green]Updated dataset for job {job_name} to {dataset_id}[/green]")
        return True
    
    def remove_dataset(self, dataset_id: str, force: bool = False) -> bool:
        """
        Remove a dataset.
        
        Args:
            dataset_id: ID of the dataset to remove
            force: If True, remove the dataset even if it's used by jobs
            
        Returns:
            True if the dataset was removed successfully, False otherwise
        """
        # Check if the dataset exists
        datasets = self.get_datasets()
        if dataset_id not in datasets:
            console.print(f"[red]Dataset {dataset_id} not found.[/red]")
            console.print("[yellow]Use /finetune datasets to see available datasets.[/yellow]")
            return False
        
        # Check if any jobs are using this dataset
        jobs_using_dataset = []
        for job_name, job in self.config.get("jobs", {}).items():
            if job.get("dataset_id") == dataset_id:
                jobs_using_dataset.append(job_name)
        
        if jobs_using_dataset and not force:
            console.print(f"[yellow]Dataset {dataset_id} is used by the following jobs:[/yellow]")
            for job_name in jobs_using_dataset:
                console.print(f"  - {job_name}")
            console.print("[yellow]Use --force to remove the dataset anyway.[/yellow]")
            return False
        
        # Remove the dataset file
        dataset_path = datasets[dataset_id].get("path")
        if dataset_path and os.path.exists(dataset_path):
            try:
                os.remove(dataset_path)
                # Remove parent directory if empty
                parent_dir = os.path.dirname(dataset_path)
                if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not remove dataset file: {str(e)}[/yellow]")
        
        # If force is True, update any jobs using this dataset
        if force and jobs_using_dataset:
            console.print(f"[yellow]Updating jobs that were using dataset {dataset_id}:[/yellow]")
            for job_name in jobs_using_dataset:
                self.config["jobs"][job_name].pop("dataset_id", None)
                self.config["jobs"][job_name].pop("dataset_path", None)
                console.print(f"  - {job_name} (dataset reference removed)")
        
        # Remove the dataset from the configuration
        del self.config["datasets"][dataset_id]
        self._save_config()
        
        console.print(f"[green]Dataset {dataset_id} removed successfully[/green]")
        return True
    
    def export_job(self, name: str, target_name: Optional[str] = None) -> bool:
        """
        Export a fine-tuned model to Ollama.
        
        Args:
            name: Name of the job
            target_name: Name to use for the exported model (defaults to job name)
            
        Returns:
            True if the model was exported successfully, False otherwise
        """
        # Check if the job exists
        job = self.get_job(name)
        if not job:
            console.print(f"[red]Job {name} not found.[/red]")
            return False
        
        # Check if the job is completed
        if job.get("status") != "completed":
            console.print(f"[yellow]Job {name} is not completed (status: {job.get('status')}).[/yellow]")
            console.print("[yellow]Only completed jobs can be exported.[/yellow]")
            return False
        
        # Get the job directory
        job_dir = job.get("job_dir")
        if not job_dir or not os.path.exists(job_dir):
            console.print(f"[red]Job directory for {name} not found.[/red]")
            return False
        
        # Get the output directory
        output_dir = os.path.join(job_dir, "output")
        if not os.path.exists(output_dir):
            console.print(f"[red]Output directory for job {name} not found.[/red]")
            return False
        
        # Set the target model name
        target_name = target_name or name
        
        # Create a Modelfile
        modelfile_path = os.path.join(job_dir, "Modelfile")
        base_model = job.get("base_model", "")
        
        with open(modelfile_path, "w") as f:
            f.write(f"FROM {base_model}\n\n")
            f.write(f"# Fine-tuned model from job {name}\n")
            f.write(f"# Base model: {base_model}\n")
            f.write(f"# Created at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Add parameters section
            f.write("PARAMETER temperature 0.7\n")
            f.write("PARAMETER top_p 0.9\n")
            f.write("PARAMETER top_k 40\n")
        
        # Export the model to Ollama
        console.print(f"[yellow]Exporting model to Ollama as {target_name}...[/yellow]")
        
        try:
            # Use the Ollama CLI to create the model
            import subprocess
            result = subprocess.run(
                ["ollama", "create", target_name, "-f", modelfile_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                console.print(f"[red]Error exporting model: {result.stderr}[/red]")
                return False
            
            console.print(f"[green]Successfully exported model to Ollama as {target_name}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error exporting model: {str(e)}[/red]")
            return False
    
    def get_ollama_models(self) -> List[Dict[str, str]]:
        """
        Get a list of models available in Ollama.
        
        Returns:
            List of dictionaries with model information
        """
        from .model_utils import get_ollama_models
        return get_ollama_models()
    
    def display_status(self):
        """Display the status of the fine-tuning system."""
        # Display hardware information
        console.print("\n[bold blue]Hardware Information:[/bold blue]")
        console.print(f"Platform: [green]{self.hardware_config['platform']}[/green]")
        console.print(f"Framework: [green]{self.hardware_config['framework']}[/green]")
        
        # Display dependency status
        console.print("\n[bold blue]Dependency Status:[/bold blue]")
        if self.check_dependencies():
            console.print("[green]All required dependencies are installed.[/green]")
        else:
            console.print("[yellow]Some dependencies are missing. Run /finetune install to install them.[/yellow]")
        
        # Display dataset information
        datasets = self.get_datasets()
        console.print(f"\n[bold blue]Datasets ({len(datasets)}):[/bold blue]")
        if datasets:
            for dataset_id, dataset in datasets.items():
                if not dataset_id:  # Skip datasets with empty IDs
                    continue
                    
                # Handle both string and numeric timestamps
                created_at_raw = dataset.get("created_at", 0)
                if isinstance(created_at_raw, str):
                    created_at = created_at_raw
                else:
                    created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at_raw))
                    
                console.print(f"[green]{dataset_id}[/green] - Created: {created_at}")
                console.print(f"  Path: {dataset.get('path')}")
                console.print(f"  Original: {dataset.get('original_path')}")
        else:
            console.print("[yellow]No datasets available. Use /finetune dataset to prepare a dataset.[/yellow]")
        
        # Display job information
        jobs = self.get_jobs()
        console.print(f"\n[bold blue]Jobs ({len(jobs)}):[/bold blue]")
        if jobs:
            for job_name, job in jobs.items():
                status = job.get("status", "unknown")
                base_model = job.get("base_model", "unknown")
                dataset_id = job.get("dataset_id", "unknown")
                
                # Get status color
                if status == "running":
                    status_color = "green"
                elif status == "completed":
                    status_color = "blue"
                elif status == "paused":
                    status_color = "yellow"
                elif status == "failed":
                    status_color = "red"
                else:
                    status_color = "white"
                
                console.print(f"[bold]{job_name}[/bold] - Status: [{status_color}]{status}[/{status_color}]")
                console.print(f"  Base Model: {base_model}")
                console.print(f"  Dataset: {dataset_id}")
                
                # Display progress for running jobs
                if status == "running":
                    _, progress, _ = self.check_job_status(job_name)
                    progress_percent = int(progress * 100)
                    console.print(f"  Progress: [green]{progress_percent}%[/green]")
                    
                    # Display ETA if available
                    if "start_time" in job:
                        elapsed_time = time.time() - job["start_time"]
                        if progress > 0:
                            total_time = elapsed_time / progress
                            remaining_time = total_time - elapsed_time
                            
                            # Format remaining time
                            if remaining_time < 60:
                                eta = f"{int(remaining_time)} seconds"
                            elif remaining_time < 3600:
                                eta = f"{int(remaining_time / 60)} minutes"
                            else:
                                eta = f"{int(remaining_time / 3600)} hours {int((remaining_time % 3600) / 60)} minutes"
                            
                            console.print(f"  ETA: {eta}")
                
                # Display completion time for completed jobs
                if status == "completed" and "completed_at" in job:
                    completed_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(job["completed_at"]))
                    console.print(f"  Completed: {completed_at}")
                
                # Display error message for failed jobs
                if status == "failed":
                    _, _, error = self.check_job_status(job_name)
                    if error:
                        console.print(f"  Error: [red]{error}[/red]")
        else:
            console.print("[yellow]No jobs available. Use /finetune create to create a job.[/yellow]")
    
    def display_job_progress(self, name: str):
        """
        Display the progress of a fine-tuning job.
        
        Args:
            name: Name of the job
        """
        # Check if the job exists
        job = self.get_job(name)
        if not job:
            console.print(f"[red]Job {name} not found.[/red]")
            return
        
        # Get the job status
        status, progress, error = self.check_job_status(name)
        
        # Display job information
        console.print(f"\n[bold blue]Job: {name}[/bold blue]")
        
        # Get status color
        if status == "running":
            status_color = "green"
        elif status == "completed":
            status_color = "blue"
        elif status == "paused":
            status_color = "yellow"
        elif status == "failed":
            status_color = "red"
        else:
            status_color = "white"
        
        console.print(f"Status: [{status_color}]{status}[/{status_color}]")
        console.print(f"Base Model: {job.get('base_model', 'unknown')}")
        console.print(f"Dataset: {job.get('dataset_id', 'unknown')}")
        
        # Display parameters
        console.print("\n[bold]Parameters:[/bold]")
        for param_name, param_value in job.get("parameters", {}).items():
            console.print(f"  {param_name}: {param_value}")
        
        # Display progress for running jobs
        if status == "running":
            progress_percent = int(progress * 100)
            
            # Create a progress bar
            bar_width = 50
            filled_width = int(bar_width * progress)
            bar = "█" * filled_width + "░" * (bar_width - filled_width)
            
            console.print(f"\n[bold]Progress: {progress_percent}%[/bold]")
            console.print(f"[green]{bar}[/green]")
            
            # Display ETA if available
            if "start_time" in job:
                elapsed_time = time.time() - job["start_time"]
                if progress > 0:
                    total_time = elapsed_time / progress
                    remaining_time = total_time - elapsed_time
                    
                    # Format times
                    if elapsed_time < 60:
                        elapsed = f"{int(elapsed_time)} seconds"
                    elif elapsed_time < 3600:
                        elapsed = f"{int(elapsed_time / 60)} minutes {int(elapsed_time % 60)} seconds"
                    else:
                        elapsed = f"{int(elapsed_time / 3600)} hours {int((elapsed_time % 3600) / 60)} minutes"
                    
                    if remaining_time < 60:
                        eta = f"{int(remaining_time)} seconds"
                    elif remaining_time < 3600:
                        eta = f"{int(remaining_time / 60)} minutes {int(remaining_time % 60)} seconds"
                    else:
                        eta = f"{int(remaining_time / 3600)} hours {int((remaining_time % 3600) / 60)} minutes"
                    
                    console.print(f"Elapsed Time: {elapsed}")
                    console.print(f"Estimated Time Remaining: {eta}")
        
        # Display completion time for completed jobs
        if status == "completed" and "completed_at" in job:
            completed_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(job["completed_at"]))
            console.print(f"\nCompleted: {completed_at}")
            
            # Display elapsed time if start_time is available
            if "start_time" in job:
                elapsed_time = job["completed_at"] - job["start_time"]
                if elapsed_time < 60:
                    elapsed = f"{int(elapsed_time)} seconds"
                elif elapsed_time < 3600:
                    elapsed = f"{int(elapsed_time / 60)} minutes {int(elapsed_time % 60)} seconds"
                else:
                    elapsed = f"{int(elapsed_time / 3600)} hours {int((elapsed_time % 3600) / 60)} minutes"
                
                console.print(f"Total Time: {elapsed}")
        
        # Display error message for failed jobs
        if status == "failed" and error:
            console.print(f"\n[red]Error: {error}[/red]")
        
        # Display log file path if available
        if "log_file" in job and os.path.exists(job["log_file"]):
            console.print(f"\nLog File: {job['log_file']}")
