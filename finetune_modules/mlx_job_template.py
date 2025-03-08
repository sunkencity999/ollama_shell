#!/usr/bin/env python
"""
MLX Fine-tuning Job Template

This script serves as a template for MLX fine-tuning jobs.
It will be copied to the job directory and used for fine-tuning.
"""

import os
import sys
import time
import json
import argparse
import subprocess
from pathlib import Path

# Function to run MLX-LM fine-tuning
def run_mlx_training(model_name, dataset_path, output_dir, batch_size, learning_rate, max_steps, log_file):
    # Open log file for writing
    with open(log_file, "w") as f:
        f.write(f"Starting fine-tuning of {model_name}\n")
        f.write(f"Parameters: batch_size={batch_size}, learning_rate={learning_rate}\n")
        f.write(f"Dataset: {dataset_path}\n\n")
        f.flush()
        
        try:
            # Check if mlx is installed and accessible
            try:
                import mlx
                f.write("MLX is properly installed\n")
                f.flush()
            except ImportError as e:
                f.write(f"Error importing MLX: {e}\n")
                f.write("MLX must be installed to continue\n")
                return False
            
            # Check for finetune.py in the application's root directory
            app_root = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), '..'))
            app_finetune_script = os.path.join(app_root, "finetune.py")
            
            if os.path.exists(app_finetune_script):
                f.write(f"Found finetune script in app root: {app_finetune_script}\n")
                finetune_script = app_finetune_script
            else:
                # Fallback to checking MLX-LM installation paths
                mlx_lm_paths = [
                    "/tmp/mlx-examples/llms",  # Source installation path
                    os.path.expanduser("~/mlx-examples/llms"),  # Alternative source path
                ]
                
                finetune_script = None
                for path in mlx_lm_paths:
                    potential_script = os.path.join(path, "mlx_lm/finetune.py")
                    if os.path.exists(potential_script):
                        finetune_script = potential_script
                        f.write(f"Found MLX-LM finetune script at {potential_script}\n")
                        break
            
            if finetune_script:
                # Direct script execution
                cmd = [
                    sys.executable, finetune_script,
                    "--model", model_name,
                    "--train-file", dataset_path,
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
                    sys.executable, "-m", "mlx_lm.finetune",
                    "--model", model_name,
                    "--train-file", dataset_path,
                    "--ollama",  # Use Ollama API to get the model
                    "--batch-size", str(batch_size),
                    "--learning-rate", str(learning_rate),
                    "--max-steps", str(max_steps),
                    "--save-every", "10",
                    "--output-dir", output_dir
                ]
            
            f.write(f"Running command: {' '.join(cmd)}\n\n")
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
                                f.write(f"Step: {current_step}/{max_steps} - Loss: {loss:.4f}\n")
                                f.flush()
                                
                                # Every 10 steps, add more detailed info
                                if current_step % 10 == 0:
                                    progress = current_step / max_steps * 100
                                    remaining = (max_steps - current_step) * (time.time() - start_time) / current_step if current_step > 0 else 0
                                    f.write(f"Completed {progress:.1f}% of training\n")
                                    f.write(f"Estimated time remaining: {remaining:.1f} seconds\n\n")
                                    f.flush()
                    except Exception as e:
                        f.write(f"Error parsing progress: {e}\n")
                        f.flush()
            
            # Wait for process to complete
            return_code = process.wait()
            
            if return_code == 0:
                f.write("\nTraining complete!\n")
                f.write(f"Model saved to {output_dir}\n")
                return True
            else:
                f.write(f"\nTraining failed with return code {return_code}\n")
                return False
                
        except Exception as e:
            f.write(f"Error during training: {str(e)}\n")
            return False

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="MLX Fine-tuning Job")
    parser.add_argument("--model", required=True, help="Model name to fine-tune")
    parser.add_argument("--dataset-path", required=True, help="Path to training data directory")
    parser.add_argument("--output-dir", required=True, help="Output directory for the fine-tuned model")
    parser.add_argument("--batch-size", type=int, default=1, help="Batch size for training")
    parser.add_argument("--learning-rate", type=float, default=5e-5, help="Learning rate for training")
    parser.add_argument("--max-steps", type=int, default=100, help="Maximum number of training steps")
    parser.add_argument("--log-file", default="finetune.log", help="Log file path")
    
    args = parser.parse_args()
    
    # Run the training
    success = run_mlx_training(
        args.model,
        args.dataset_path,
        args.output_dir,
        args.batch_size,
        args.learning_rate,
        args.max_steps,
        args.log_file
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
