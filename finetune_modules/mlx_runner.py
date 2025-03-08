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
    
    # Create a real MLX-LM fine-tuning script
    script_path = os.path.join(job_dir, "run_finetune.py")
    with open(script_path, "w") as f:
        f.write("""
import os
import sys
import time
import json
import argparse
import subprocess
from pathlib import Path

# Fine-tuning parameters
model_name = "{model_name}"
max_steps = {max_steps}
batch_size = {batch_size}
learning_rate = {learning_rate}
dataset_path = "{dataset_path}"
output_dir = "{output_dir}"
log_file = "{log_file}"

# Function to run MLX-LM fine-tuning
def run_mlx_training():
    # Open log file for writing
    with open(log_file, "w") as f:
        f.write(f"Starting fine-tuning of {{model_name}}\\n")
        f.write(f"Parameters: batch_size={{batch_size}}, learning_rate={{learning_rate}}\\n")
        f.write(f"Dataset: {{dataset_path}}\\n\\n")
        f.flush()
        
        try:
            # Check if mlx_lm is installed and accessible
            try:
                import mlx
                f.write("MLX is properly installed\\n")
                f.flush()
            except ImportError as e:
                f.write(f"Error importing MLX: {{e}}\\n")
                f.write("MLX must be installed to continue\\n")
                return False
            
            # Check for finetune.py in the application's root directory first
            app_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            app_finetune_script = os.path.join(app_root, "finetune.py")
            
            # Also check for MLX-LM installation paths
            mlx_lm_paths = [
                "/tmp/mlx-examples/llms",  # Source installation path
                os.path.expanduser("~/mlx-examples/llms"),  # Alternative source path
            ]
            
            # Find the MLX-LM finetune script
            finetune_script = None
            for path in mlx_lm_paths:
                potential_script = os.path.join(path, "mlx_lm/finetune.py")
                if os.path.exists(potential_script):
                    finetune_script = potential_script
                    f.write(f"Found MLX-LM finetune script at {{potential_script}}\\n")
                    break
            
            if finetune_script:
                # Direct script execution
                cmd = [
                    "python", finetune_script,
                    "--model", model_name,
                    "--train-file", os.path.join("{mlx_dataset_dir}", "train.jsonl"),
                    "--ollama",  # Use Ollama API to get the model
                    "--batch-size", str(batch_size),
                    "--learning-rate", str(learning_rate),
                    "--max-steps", str(max_steps),
                    "--save-every", "10",
                    "--output-dir", output_dir
                ]
            else:
                # Try module import approach
                cmd = [
                    "python", "-m", "mlx_lm.finetune",
                    "--model", model_name,
                    "--train-file", os.path.join("{mlx_dataset_dir}", "train.jsonl"),
                    "--ollama",  # Use Ollama API to get the model
                    "--batch-size", str(batch_size),
                    "--learning-rate", str(learning_rate),
                    "--max-steps", str(max_steps),
                    "--save-every", "10",
                    "--output-dir", output_dir
                ]
            
            f.write(f"Running command: {{' '.join(cmd)}}\\n\\n")
            f.flush()
            
            # Record start time
            start_time = time.time()
            
            # Run the command and capture output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Process output in real-time
            current_step = 0
            for line in process.stdout:
                f.write(line)
                f.flush()
                
                # Try to parse progress information
                if "step" in line.lower() and "loss" in line.lower():
                    try:
                        # Extract step and loss information
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part.lower() == "step":
                                step_str = parts[i+1].rstrip(',;:')
                                current_step = int(step_str)
                            if part.lower() == "loss":
                                loss_str = parts[i+1].rstrip(',;:')
                                loss = float(loss_str)
                                f.write(f"Step: {{current_step}}/{{max_steps}} - Loss: {{loss:.4f}}\\n")
                                f.flush()
                                
                                # Every 10 steps, add more detailed info
                                if current_step % 10 == 0:
                                    progress = current_step / max_steps * 100
                                    remaining = (max_steps - current_step) * (time.time() - start_time) / current_step if current_step > 0 else 0
                                    f.write(f"Completed {{progress:.1f}}% of training\\n")
                                    f.write(f"Estimated time remaining: {{remaining:.1f}} seconds\\n\\n")
                                    f.flush()
                    except Exception as e:
                        f.write(f"Error parsing progress: {{e}}\\n")
                        f.flush()
            
            # Wait for process to complete
            return_code = process.wait()
            
            if return_code == 0:
                f.write("\\nTraining complete!\\n")
                f.write(f"Model saved to {{output_dir}}\\n")
                return True
            else:
                f.write(f"\\nTraining failed with return code {{return_code}}\\n")
                return False
                
        except Exception as e:
            f.write(f"Error during training: {{str(e)}}\\n")
            return False

# Run the training
success = run_mlx_training()

# Exit with appropriate code
sys.exit(0 if success else 1)
""".format(
            model_name=model_name,
            dataset_path=dataset_path,
            mlx_dataset_dir=mlx_dataset_dir,
            output_dir=output_dir,
            batch_size=job.get("parameters", {}).get("per_device_train_batch_size", 1),
            max_steps=job.get("parameters", {}).get("max_steps", 100),
            learning_rate=job.get("parameters", {}).get("learning_rate", 5e-5),
            log_file=os.path.join(job_dir, "finetune.log")
        ))
    
    # Make the script executable
    os.chmod(script_path, 0o755)
    
    # Command to run the script
    python_cmd = get_venv_python_cmd()
    cmd = python_cmd + [script_path]
    
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
        Tuple of (status, progress, error_message)
    """
    # Check if the process is still running
    pid = job.get("pid")
    if not pid:
        return "error", 0.0, "No process ID found for this job"
    
    try:
        # Check if the process is still running
        os.kill(pid, 0)  # This will raise an exception if the process is not running
        
        # Process is running, check the log file for progress
        log_file = job.get("log_file")
        if not log_file or not os.path.exists(log_file):
            return "running", 0.0, None
        
        # Parse the log file to extract progress
        with open(log_file, "r") as f:
            log_content = f.read()
        
        # Extract progress information
        max_steps = job.get("parameters", {}).get("max_steps", 1000)
        current_step = 0
        
        # Look for lines like "Step: 100/1000"
        import re
        step_matches = re.findall(r"Step:\s+(\d+)/(\d+)", log_content)
        if step_matches:
            current_step = int(step_matches[-1][0])
            max_steps = int(step_matches[-1][1])
        
        # Calculate progress
        progress = current_step / max_steps if max_steps > 0 else 0.0
        
        return "running", progress, None
    except ProcessLookupError:
        # Process is not running
        # Check if there's a completed model in the output directory
        output_dir = os.path.join(job_dir, "output")
        if os.path.exists(os.path.join(output_dir, "tokenizer.json")) and \
           os.path.exists(os.path.join(output_dir, "weights.safetensors")):
            return "completed", 1.0, None
        
        # Check for error in the log file
        log_file = job.get("log_file")
        error_message = None
        if log_file and os.path.exists(log_file):
            with open(log_file, "r") as f:
                log_content = f.read()
            
            # Look for error messages
            if "Error" in log_content or "Exception" in log_content:
                # Extract the error message
                error_lines = [line for line in log_content.split("\n") if "Error" in line or "Exception" in line]
                if error_lines:
                    error_message = error_lines[-1]
        
        return "failed", 0.0, error_message
    except Exception as e:
        return "error", 0.0, str(e)
