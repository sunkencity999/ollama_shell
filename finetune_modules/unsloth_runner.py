"""
Unsloth fine-tuning runner for NVIDIA GPUs.
This module provides functionality to run fine-tuning jobs using Unsloth.
"""

import os
import sys
import json
import time
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

from .venv_utils import get_venv_python_cmd, is_module_installed, run_in_venv

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


def run_unsloth(job: Dict, job_dir: str, update_progress_callback=None):
    """
    Run a fine-tuning job using Unsloth on NVIDIA GPUs.
    
    Args:
        job: Job configuration
        job_dir: Directory containing job files
        update_progress_callback: Callback function to update progress
    
    Returns:
        True if the job was started successfully, False otherwise
    """
    # Check if Unsloth is installed
    if not is_module_installed("unsloth"):
        console.print("[red]Unsloth is not installed. Please run /finetune install first.[/red]")
        return False
    
    # Get paths
    model_name = job["base_model"]
    dataset_path = job.get("dataset_path")
    
    if not dataset_path:
        console.print("[red]No dataset specified for this job.[/red]")
        return False
    
    # Check if the dataset exists
    if not os.path.exists(dataset_path):
        console.print(f"[red]Dataset not found at {dataset_path}[/red]")
        return False
    
    # Create a Python script for the fine-tuning job
    script_path = os.path.join(job_dir, "finetune_script.py")
    
    # Write the fine-tuning script
    with open(script_path, "w") as f:
        f.write(f"""
import os
import sys
import json
import time
from pathlib import Path

# Check if we're running on a system with CUDA
try:
    import torch
    has_cuda = torch.cuda.is_available()
    if has_cuda:
        print(f"CUDA available: {{torch.cuda.get_device_name(0)}}")
    else:
        print("CUDA not available, falling back to CPU")
except ImportError:
    has_cuda = False
    print("PyTorch not installed, falling back to CPU")

# Load the dataset
dataset_path = "{dataset_path}"
with open(dataset_path, "r") as f:
    dataset = json.load(f)

# Import Unsloth
try:
    from unsloth import FastLanguageModel
    from datasets import Dataset
    import transformers
    from transformers import TrainingArguments
    
    # Convert the dataset to HuggingFace format
    hf_dataset = Dataset.from_list(dataset)
    
    # Load the model
    model_name = "{model_name}"
    
    # Check if it's a local model or a HuggingFace model
    if "/" not in model_name:
        # Assume it's a local Ollama model
        print(f"Using local model: {{model_name}}")
        # For local models, we need to use a HuggingFace model as a base
        # and then fine-tune it
        model_name = "meta-llama/Llama-2-7b-hf"  # Default base model
    
    # Set up the model and tokenizer
    max_seq_length = {job["parameters"].get("max_seq_length", 2048)}
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=None,  # None for auto detection, torch.float16 for fp16
        load_in_4bit=True,  # Use 4bit quantization to reduce memory usage
    )
    
    # Set up LoRA fine-tuning
    model = FastLanguageModel.get_peft_model(
        model,
        r={job["parameters"].get("lora_r", 16)},
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", 
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha={job["parameters"].get("lora_alpha", 32)},
        lora_dropout={job["parameters"].get("lora_dropout", 0.05)},
    )
    
    # Prepare the dataset
    def formatting_func(example):
        text = example["text"]
        return text
    
    # Tokenize the dataset
    tokenized_dataset = FastLanguageModel.get_tokenized_dataset(
        tokenizer=tokenizer,
        dataset=hf_dataset,
        formatting_func=formatting_func,
        max_seq_length=max_seq_length,
    )
    
    # Set up training arguments
    training_args = TrainingArguments(
        output_dir="{os.path.join(job_dir, "output")}",
        num_train_epochs={job["parameters"].get("num_train_epochs", 3)},
        per_device_train_batch_size={job["parameters"].get("per_device_train_batch_size", 2)},
        gradient_accumulation_steps={job["parameters"].get("gradient_accumulation_steps", 4)},
        gradient_checkpointing=True,
        optim="adamw_torch",
        logging_steps=10,
        save_strategy="epoch",
        learning_rate={job["parameters"].get("learning_rate", 2e-4)},
        weight_decay={job["parameters"].get("weight_decay", 0.01)},
        fp16=True,
        bf16=False,
        max_grad_norm=0.3,
        warmup_ratio=0.03,
        lr_scheduler_type="constant",
        report_to="none",
    )
    
    # Create a progress tracking file
    progress_file = "{os.path.join(job_dir, "progress.json")}"
    
    # Define a custom callback to track progress
    class ProgressCallback(transformers.TrainerCallback):
        def __init__(self):
            self.start_time = time.time()
            self.step_times = []
        
        def on_step_end(self, args, state, control, **kwargs):
            # Calculate progress
            progress = state.global_step / state.max_steps
            
            # Calculate ETA
            current_time = time.time()
            step_time = current_time - self.start_time
            self.start_time = current_time
            
            # Keep track of the last 10 step times
            self.step_times.append(step_time)
            if len(self.step_times) > 10:
                self.step_times.pop(0)
            
            # Calculate average step time
            avg_step_time = sum(self.step_times) / len(self.step_times)
            
            # Calculate ETA
            steps_remaining = state.max_steps - state.global_step
            eta_seconds = avg_step_time * steps_remaining
            
            # Write progress to file
            with open(progress_file, "w") as f:
                json.dump({
                    "progress": progress,
                    "step": state.global_step,
                    "max_steps": state.max_steps,
                    "eta_seconds": eta_seconds
                }, f)
    
    # Set up the trainer
    trainer = FastLanguageModel.get_trainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=tokenized_dataset,
        args=training_args,
        callbacks=[ProgressCallback()],
    )
    
    # Start training
    trainer.train()
    
    # Save the model
    output_dir = "{os.path.join(job_dir, "output")}"
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    # Write a completion file
    with open("{os.path.join(job_dir, "completed")}", "w") as f:
        f.write("Training completed successfully")
    
    print("Training completed successfully")
except Exception as e:
    # Write the error to a file
    with open("{os.path.join(job_dir, "error.txt")}", "w") as f:
        f.write(str(e))
    print(f"Error during training: {{str(e)}}")
    sys.exit(1)
""")
    
    # Create a log file
    log_file = os.path.join(job_dir, "finetune.log")
    
    # Start the process
    python_cmd = get_venv_python_cmd()
    cmd = python_cmd + [script_path]
    
    console.print(f"[green]Starting Unsloth fine-tuning with command: {' '.join(cmd)}[/green]")
    
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


def check_unsloth_job_status(job: Dict, job_dir: str) -> Tuple[str, float, Optional[str]]:
    """
    Check the status of an Unsloth fine-tuning job.
    
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
        
        # Process is running, check the progress file
        progress_file = os.path.join(job_dir, "progress.json")
        if os.path.exists(progress_file):
            try:
                with open(progress_file, "r") as f:
                    progress_data = json.load(f)
                
                progress = progress_data.get("progress", 0.0)
                return "running", progress, None
            except Exception:
                # If we can't read the progress file, just report the job as running
                return "running", 0.0, None
        else:
            # No progress file yet, job is still initializing
            return "running", 0.0, None
    except ProcessLookupError:
        # Process is not running
        # Check if there's a completed file
        if os.path.exists(os.path.join(job_dir, "completed")):
            return "completed", 1.0, None
        
        # Check for error file
        error_file = os.path.join(job_dir, "error.txt")
        if os.path.exists(error_file):
            with open(error_file, "r") as f:
                error_message = f.read()
            return "failed", 0.0, error_message
        
        # Check the log file for errors
        log_file = job.get("log_file")
        if log_file and os.path.exists(log_file):
            with open(log_file, "r") as f:
                log_content = f.read()
            
            if "Error" in log_content or "Exception" in log_content:
                # Extract the error message
                error_lines = [line for line in log_content.split("\n") if "Error" in line or "Exception" in line]
                if error_lines:
                    return "failed", 0.0, error_lines[-1]
        
        # If we can't determine what happened, assume the job failed
        return "failed", 0.0, "Job terminated unexpectedly"
    except Exception as e:
        return "error", 0.0, str(e)
