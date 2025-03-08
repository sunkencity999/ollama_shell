"""
MLX-LM fine-tuning runner for Apple Silicon.
This module provides functionality to run fine-tuning jobs using MLX-LM.
"""

import os
import sys
import json
import time
import shutil
import subprocess
import tempfile
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

from .venv_utils import get_venv_python_cmd, is_module_installed, run_in_venv
from .model_utils import export_ollama_model

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


def run_mlx_lm(job: Dict, job_dir: str, update_progress_callback=None):
    """
    Run a fine-tuning job using MLX-LM on Apple Silicon.
    
    Args:
        job: Job configuration
        job_dir: Directory containing job files
        update_progress_callback: Callback function to update progress
    
    Returns:
        True if the job was started successfully, False otherwise
    """
    # Check if MLX-LM is installed
    if not is_module_installed("mlx"):
        console.print("[red]MLX is not installed. Please run /finetune install first.[/red]")
        return False
    
    # Get paths
    model_name = job.get("base_model", "")
    dataset_path = job.get("dataset_path", "")
    
    if not dataset_path:
        console.print("[red]No dataset specified for this job.[/red]")
        return False
    
    # Check if the dataset exists
    if not os.path.exists(dataset_path):
        console.print(f"[red]Dataset not found at {dataset_path}[/red]")
        return False
    
    # Prepare MLX-LM dataset directory
    mlx_dataset_dir = os.path.join(job_dir, "mlx_dataset")
    os.makedirs(mlx_dataset_dir, exist_ok=True)
    
    # Check dataset format and convert if needed
    if os.path.isdir(dataset_path):
        # Check if this is already an MLX-LM formatted dataset
        if os.path.exists(os.path.join(dataset_path, "train.jsonl")):
            console.print("[green]Using existing MLX-LM formatted dataset.[/green]")
            mlx_dataset_dir = dataset_path
        else:
            console.print("[red]Directory dataset not in MLX-LM format. Please provide a valid dataset.[/red]")
            return False
    elif dataset_path.endswith(".jsonl"):
        # Copy the JSONL file to the MLX dataset directory as train.jsonl
        shutil.copy(dataset_path, os.path.join(mlx_dataset_dir, "train.jsonl"))
        console.print(f"[green]Copied dataset to {mlx_dataset_dir}/train.jsonl[/green]")
    elif dataset_path.endswith(".json"):
        # Try to convert JSON to JSONL format
        try:
            with open(dataset_path, "r") as f:
                data = json.load(f)
            
            # Check if it's a list of dictionaries
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                with open(os.path.join(mlx_dataset_dir, "train.jsonl"), "w") as f:
                    for item in data:
                        f.write(json.dumps(item) + "\n")
                console.print(f"[green]Converted JSON dataset to JSONL format at {mlx_dataset_dir}/train.jsonl[/green]")
            else:
                console.print("[red]JSON dataset is not in the expected format (list of dictionaries).[/red]")
                return False
        except Exception as e:
            console.print(f"[red]Error converting JSON dataset: {str(e)}[/red]")
            return False
    else:
        console.print("[red]Unsupported dataset format. Please provide a .jsonl or .json file.[/red]")
        return False
    
    # Use the Ollama model name directly with the Ollama API
    model_dir = os.path.join(job_dir, "model")
    os.makedirs(model_dir, exist_ok=True)
    
    console.print(f"[yellow]Using Ollama model {model_name} for fine-tuning...[/yellow]")
    
    # Write the model name to a file for reference
    with open(os.path.join(model_dir, "model_name.txt"), "w") as f:
        f.write(model_name)
    
    # Set up output directory
    output_dir = os.path.join(job_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Use our pre-made MLX job template for fine-tuning
    script_path = os.path.join(job_dir, "run_finetune.py")
    template_path = os.path.join(os.path.dirname(__file__), "mlx_job_template.py")
    
    # Check if the template exists
    if not os.path.exists(template_path):
        console.print(f"[red]Error: MLX job template not found at {template_path}[/red]")
        return False
        
    # Copy the template to the job directory
    shutil.copy(template_path, script_path)
    
    # Make the script executable
    os.chmod(script_path, 0o755)
    
    # Command to run the script with proper parameters
    python_cmd = get_venv_python_cmd()
    cmd = python_cmd + [
        script_path,
        "--model", model_name,
        "--dataset-path", os.path.join(mlx_dataset_dir, "train.jsonl"),
        "--output-dir", output_dir,
        "--batch-size", str(job.get("parameters", {}).get("per_device_train_batch_size", 1)),
        "--learning-rate", str(job.get("parameters", {}).get("learning_rate", 5e-5)),
        "--max-steps", str(job.get("parameters", {}).get("max_steps", 100)),
        "--log-file", os.path.join(job_dir, "finetune.log")
    ]
    
    # Start the process
    console.print(f"[green]Starting MLX-LM fine-tuning with command: {' '.join(cmd)}[/green]")
    
    # Create a log file
    log_file = os.path.join(job_dir, "finetune.log")
    
    try:
        # Start the process and redirect output to the log file
        with open(log_file, "w") as f:
            process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)
        
        # Store the process ID
        with open(os.path.join(job_dir, "process.pid"), "w") as f:
            f.write(str(process.pid))
        
        console.print(f"[green]Fine-tuning job started with PID {process.pid}[/green]")
        console.print(f"[green]Logs are being written to {log_file}[/green]")
        
        # Update job status
        job["status"] = "running"
        job["pid"] = process.pid
        job["start_time"] = time.time()
        job["log_file"] = log_file
        
        return True
    except Exception as e:
        console.print(f"[red]Error starting fine-tuning job: {str(e)}[/red]")
        return False


def check_mlx_job_status(job: Dict, job_dir: str) -> Tuple[str, float, Optional[str]]:
    """
    Check the status of an MLX-LM fine-tuning job.
    
    Args:
        job: Job configuration
        job_dir: Directory containing job files
    
    Returns:
        Tuple of (status, progress, message)
    """
    pid = job.get("pid")
    log_file = job.get("log_file")
    
    if not pid or not log_file:
        return "error", 0.0, "Job information is incomplete"
    
    # Check if the process is still running
    try:
        os.kill(pid, 0)  # Signal 0 is used to check if process exists
        is_running = True
    except OSError:
        is_running = False
    
    # Check the log file for progress information
    progress = 0.0
    message = None
    
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f:
                log_content = f.read()
            
            # Try to extract progress information
            max_steps = job.get("parameters", {}).get("max_steps", 100)
            
            # Look for step information
            step_matches = re.findall(r"Step: (\d+)/(\d+)", log_content)
            if step_matches:
                current_step = int(step_matches[-1][0])
                total_steps = int(step_matches[-1][1])
                progress = min(current_step / total_steps * 100, 99.9)
                message = f"Step {current_step}/{total_steps}"
            
            # Check for completion
            if "Training complete!" in log_content:
                return "completed", 100.0, "Training complete"
            
            # Check for errors
            if "Error" in log_content or "error" in log_content:
                error_lines = [line for line in log_content.split("\n") if "Error" in line or "error" in line]
                if error_lines:
                    return "error", 0.0, error_lines[-1]
        
        except Exception as e:
            return "error", 0.0, f"Error reading log file: {str(e)}"
    
    if is_running:
        return "running", progress, message
    else:
        # Process is not running
        if progress >= 99.0:
            return "completed", 100.0, "Training complete"
        else:
            return "error", progress, "Process terminated unexpectedly"


def export_mlx_model(job: Dict, job_dir: str) -> bool:
    """
    Export an MLX-LM fine-tuned model to Ollama.
    
    Args:
        job: Job configuration
        job_dir: Directory containing job files
    
    Returns:
        True if the model was exported successfully, False otherwise
    """
    # Check if the model exists
    output_dir = os.path.join(job_dir, "output")
    if not os.path.exists(output_dir) or not os.listdir(output_dir):
        console.print("[red]No fine-tuned model found in the output directory.[/red]")
        return False
    
    # Get the base model name
    model_name = job.get("base_model", "")
    if not model_name:
        console.print("[red]Base model name not found in job configuration.[/red]")
        return False
    
    # Get the job name for the new model
    job_name = job.get("name", "")
    if not job_name:
        console.print("[red]Job name not found in job configuration.[/red]")
        return False
    
    # Create a Modelfile for the fine-tuned model
    modelfile_path = os.path.join(job_dir, "Modelfile")
    with open(modelfile_path, "w") as f:
        f.write(f"FROM {model_name}\n")
        f.write(f"TEMPLATE \"{{prompt}}\"\n")
        f.write(f"PARAMETER stop \"\"\n")
        f.write(f"PARAMETER stop \"\n\"\n")
        f.write(f"PARAMETER temperature 0.7\n")
        f.write(f"PARAMETER top_p 0.9\n")
        f.write(f"PARAMETER top_k 40\n")
    
    # Export the model to Ollama
    return export_ollama_model(job_name, modelfile_path, output_dir)
